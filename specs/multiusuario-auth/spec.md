# Spec: Multiusuário, Autenticação (JWT) e Reorganização do módulo agente

**Status:** Aprovado
**Feature:** multiusuario-auth
**Origem:** `specs/multiusuario-auth/negocio.md`

## Contexto

Hoje a aplicação tem três módulos: `app/` (agente WhatsApp — entrypoint, agents,
services, repositories, models, integrations), `backend/` (FastAPI com as APIs do
dashboard) e `frontend/` (Flask que consome o backend via httpx).

O sistema é **single-user na prática**:

- O webhook só aceita um número (`WHATSAPP_ALLOWED_NUMBER`); qualquer outro é ignorado.
- A tabela `transacoes` tem uma coluna `responsavel` (string, default `"Jhonatas"`),
  mas ela é apenas descritiva — **não há tabela de usuários, nem vínculo, nem login**.
- O `frontend/` e o `backend/` são **abertos**: qualquer um que alcance as portas vê
  todos os dados. Não há autenticação em nenhuma camada.

Esta feature introduz **usuários de verdade**, **login com JWT** e move o agente para
`agent/`, sem reescrever as regras financeiras existentes.

**Decisões travadas com o solicitante:**

- Diretório do agente: `app/` → **`agent/`**.
- WhatsApp permanece **single-number por ora** (`WHATSAPP_ALLOWED_NUMBER` continua),
  sem nada novo no agente; mas o **schema já nasce multiusuário** (FK `usuario_id`).
- **JWT** emitido pelo backend no login; frontend guarda e envia como `Bearer`.
  **Access token + refresh token** no padrão de mercado.
- **Backend exige o token** em endpoints protegidos e **filtra os dados pelo
  `usuario_id` do token** (defesa em profundidade, não confia só na rede).
- **Cadastro só via script**; o frontend tem **apenas modal de login** (sem cadastro).
- **Login por e-mail.** Hash de senha com **bcrypt**.
- **RBAC:** dois papéis — **`ADMIN`** e **`USER`**. O usuário padrão (Jhonatas,
  `jhonatas2004@gmail.com`) nasce como **`ADMIN`**.
- Sessão do JWT **server-side no Flask** (cookie `HttpOnly`).
- `responsavel` (string) **permanece campo livre** — é quem realizou o gasto, podendo
  diferir do dono da conta; não se confunde com `usuario_id`.

---

## Fora de Escopo

- Tela/modal de **cadastro** ou auto-registro pela web — usuários comuns nascem por
  script (o ADMIN também pode criar via CRUD — RF-09).
- Recuperação de senha, verificação de e-mail, 2FA, OAuth social.
- **Multi-número no WhatsApp** (vários usuários lançando por WhatsApp) — o desenho
  fica preparado, mas a ativação de fato é fora de escopo agora.
- Reescrita das regras financeiras (parcelas, embeddings, projeção, math em `Decimal`).
- Mudança de tecnologia do frontend (continua Flask) ou do backend (continua FastAPI).

---

## Requisitos Funcionais

### RF-01 · Reorganização do agente: `app/` → `agent/`

Mover o pacote `app/` inteiro para `agent/`, preservando a estrutura interna
(`entrypoint/`, `agents/`, `services/`, `repositories/`, `models/`, `integrations/`,
`config.py`).

- Atualizar **todos os imports** (`app.` → `agent.`) em código, testes e scripts.
- Atualizar **alembic** (`env.py`, `script.py.mako`, qualquer `target_metadata`),
  `start.py`, `pyproject.toml` (entrypoints/pacotes), `CLAUDE.md` e `README.md`.
- O comando de subida do agente passa a referenciar `agent.entrypoint.main:app`.
- **Nenhuma mudança de comportamento** — é renomeação/movimentação pura.

**Critérios de aceitação:**

- [ ] Não existe mais o diretório `app/`; o agente roda de `agent/`
- [ ] `uv run pytest tests/ -v` passa sem nenhum import a `app.`
- [ ] `grep -r "app\."` não retorna imports do antigo pacote (em código/teste/config)
- [ ] Alembic ainda enxerga a metadata e `alembic upgrade head` funciona
- [ ] `start.py` sobe o agente apontando para `agent.entrypoint.main:app`

### RF-02 · Tabela de usuários (`usuarios`)

Nova tabela `usuarios` (via migration Alembic) com os campos:

- `id` (PK)
- `nome` (nome da pessoa)
- `username` (nome de usuário)
- `email` (**identificador de login**, único, NOT NULL)
- `senha_hash` (bcrypt)
- `telefone` / `whatsapp_numero` (único quando presente)
- `role` (`ADMIN` | `USER`, NOT NULL, default `USER`)
- `ativo` (bool, default true)
- `criado_em`

Senha **nunca** armazenada em texto — apenas hash bcrypt.

**Critérios de aceitação:**

- [ ] Migration cria `usuarios` com `email` único e `role` (ADMIN/USER)
- [ ] Não há coluna de senha em texto puro; só `senha_hash` (bcrypt)
- [ ] `telefone`/`whatsapp_numero` é único quando preenchido
- [ ] Inserir um usuário com `email` duplicado falha

### RF-03 · Vínculo de transações ao usuário

`transacoes` ganha `usuario_id` (FK → `usuarios.id`), **NOT NULL**.

- Migration de **backfill**: todas as transações existentes vão para o usuário padrão
  **Jhonatas** (`jhonatas2004@gmail.com`, role `ADMIN`).
- O agente, ao cadastrar, grava o `usuario_id` do usuário dono do número autorizado
  (hoje, o usuário padrão).
- A coluna `responsavel` (string) **permanece como campo livre** — representa quem
  realizou o gasto (pode ser outra pessoa que comprou na conta do usuário). O vínculo
  de propriedade/isolamento é o `usuario_id`; `responsavel` é só descritivo.

**Critérios de aceitação:**

- [ ] Após a migration, nenhuma transação fica com `usuario_id` nulo
- [ ] Transação criada pelo agente nasce com o `usuario_id` correto
- [ ] Consultas do agente/serviços continuam funcionando para o usuário padrão

### RF-04 · Cadastro de usuário via script

Script CLI em `scripts/` que cria um usuário: recebe `nome`, `username`, `email`,
`senha`, `telefone` (opcional) e `role` (default `USER`); grava com a senha
**hasheada (bcrypt)**.

- Erro claro se o `email` já existir.
- Saída informando as credenciais criadas (para o usuário usar no login).
- Permite criar o **usuário admin padrão** (Jhonatas, `jhonatas2004@gmail.com`,
  role `ADMIN`) — a senha será fornecida no momento da execução.

**Critérios de aceitação:**

- [ ] `uv run python scripts/criar_usuario.py ...` cria um usuário com senha bcrypt
- [ ] É possível definir `role=ADMIN` pelo script
- [ ] Tentar criar com `email` duplicado falha com mensagem clara
- [ ] A senha gravada não é recuperável (hash one-way verificável no login)

### RF-05 · Autenticação no backend (JWT)

O backend FastAPI ganha um módulo de autenticação com **access + refresh token**
(padrão de mercado):

- `POST /auth/login` — recebe `email` + senha, valida contra `usuarios` (bcrypt),
  retorna **access token** (curta duração) e **refresh token** (longa duração). O
  access token (HS256) contém `sub = usuario_id`, `role` e `exp`.
- `POST /auth/refresh` — recebe um refresh token válido e devolve um novo access token
  (e rotaciona o refresh, conforme boa prática).
- `POST /auth/logout` — invalida o refresh token corrente.
- Dependência de segurança (`Depends`) que valida o `Authorization: Bearer <access>`,
  rejeita ausente/expirado/inválido com **401**, e injeta `usuario_id` + `role`.
- **Todos os endpoints de dados** (`/api/transacoes*`, `/api/grafico/*`, resumo,
  projeção, parcelas) são protegidos e **filtram por `usuario_id` do token**.
- Segredo do JWT e TTLs (access/refresh) via `pydantic-settings` (`.env`), nunca
  hardcoded.

**Critérios de aceitação:**

- [ ] `POST /auth/login` com credenciais válidas retorna access + refresh; inválidas → 401
- [ ] `POST /auth/refresh` troca um refresh válido por um novo access token
- [ ] Endpoint de dados sem `Bearer` válido (ausente/expirado) → 401
- [ ] Dois usuários distintos veem **apenas suas próprias** transações no mesmo endpoint
- [ ] Access token expira no TTL configurado; refresh permite renovar sem novo login
- [ ] Segredo/TTLs do JWT vêm de config; não há segredo no código

### RF-06 · Login no frontend (modal) e sessão

O frontend Flask ganha **modal de login** e proteção de rotas:

- Modal simples: identificador + senha → chama `POST /auth/login` do backend via httpx.
- O JWT recebido é guardado na **sessão do Flask** (cookie de sessão assinado,
  `HttpOnly`); o `backend_client` passa a enviar `Authorization: Bearer` em toda chamada.
- Rotas do dashboard exigem sessão válida; sem login, redireciona/abre o modal.
- **Logout** que limpa a sessão.
- Sem modal de cadastro.

**Critérios de aceitação:**

- [ ] Acessar o dashboard sem login leva ao modal/login
- [ ] Login com credenciais geradas pelo script dá acesso ao painel do usuário
- [ ] As chamadas do frontend ao backend levam o `Bearer` do usuário logado
- [ ] Logout encerra a sessão; o painel volta a exigir login
- [ ] O dashboard mostra somente os dados do usuário logado

### RF-07 · Configuração e `start.py`

- Novas variáveis em `.env`/`.env.example`: `JWT_SECRET`, `JWT_ACCESS_EXPIRES_MIN`,
  `JWT_REFRESH_EXPIRES_DAYS`, `ADMIN_EMAILS` (allowlist do RF-08) e `SECRET_KEY` da
  sessão Flask. Sem valores reais commitados.
- `start.py` continua subindo agente/backend/frontend; só ajustar referências de
  pacote (`agent.`) e garantir que as novas configs são lidas.

**Critérios de aceitação:**

- [ ] `.env.example` documenta as novas variáveis
- [ ] App não sobe se `JWT_SECRET`/`SECRET_KEY` faltarem (falha explícita)
- [ ] `uv run python start.py` sobe tudo com a nova organização

### RF-08 · Autorização e papéis (RBAC)

Além da autenticação, regras de autorização explícitas:

- **Isolamento por dono (USER):** todo acesso a transação de um `USER` é filtrado por
  `usuario_id` do token. Um `USER` **nunca** lê, edita ou exclui transação de outro —
  mesmo passando um `id` alheio (resposta **403/404**, não vaza existência).
- **Dois papéis:**
  - `USER` — acessa apenas o próprio painel/transações.
  - `ADMIN` — **acesso master**: ignora o filtro de dono e pode operar sobre os dados
    de **qualquer** usuário (ver RF-09). O usuário Jhonatas é `ADMIN` por padrão.
- A `role` viaja no access token e é verificada no servidor (fonte da decisão é o
  token validado, nunca um parâmetro enviado pelo cliente).
- **Check extra para o ADMIN (defesa em profundidade):** por ter acesso a tudo, as
  rotas administrativas exigem, além de `role=ADMIN` no token, uma **validação
  adicional da credencial do admin** — o e-mail do `sub` é reconferido contra o
  registro em `usuarios` (role ainda é ADMIN e usuário ativo) **e** contra um
  **allowlist de e-mails admin** configurado em `.env` (`ADMIN_EMAILS`). Falha em
  qualquer checagem → **403**.

**Critérios de aceitação:**

- [ ] `USER` que tenta acessar transação de outro usuário recebe 403/404
- [ ] Rota administrativa acessada por `USER` → 403
- [ ] `ADMIN` (com e-mail no allowlist e ativo) acessa as rotas administrativas
- [ ] Token forjado com `role=ADMIN` cujo e-mail não está no allowlist → 403
- [ ] A `role`/credencial são revalidadas no servidor, não confiando só no claim

### RF-09 · CRUD administrativo de usuários e transações

O ADMIN tem um conjunto de rotas protegidas (todas sob o check do RF-08) para
gerência completa:

- **Usuários (CRUD):** criar, listar, obter, editar (nome, username, telefone, email,
  role, ativo; resetar senha) e excluir/inativar usuários. Espelha e complementa o
  script `criar_usuario.py` pela API.
- **Transações de qualquer usuário (CRUD):** o ADMIN pode listar/obter/criar/editar/
  excluir transações de **qualquer** `usuario_id`, informando o usuário alvo.
- Excluir usuário faz **cascade**: as transações dele são apagadas junto (FK
  `ON DELETE CASCADE` / exclusão em transação no service).
- **Sem tela de administração** nesta fase — o CRUD admin é **só API**.

**Critérios de aceitação:**

- [ ] ADMIN cria/lista/edita/exclui usuários via API protegida
- [ ] ADMIN lê e altera transações de outro usuário informando o alvo
- [ ] As mesmas rotas negadas a `USER` (403)
- [ ] Editar usuário permite trocar `role` e `ativo`; resetar senha gera novo hash
- [ ] Excluir usuário faz cascade nas transações dele (sem dados órfãos)
- [ ] Não há tela de administração no frontend (apenas API)

---

## Bibliotecas propostas (a confirmar no planejamento)

- **JWT:** `PyJWT` (simples, sem dependências pesadas) — emissão/validação HS256,
  com access + refresh token.
- **Hash de senha:** `passlib[bcrypt]` (ou `bcrypt` direto) — algoritmo bcrypt.
- **Frontend:** sessão nativa do Flask (`flask.session`, cookie assinado `HttpOnly`)
  — sem Flask-Login, já que o "login" é só guardar os tokens do backend.

---

## Contratos a congelar no planejamento

- **`schema-usuarios`**: DDL de `usuarios`, FK `usuario_id` em `transacoes`,
  estratégia de backfill do usuário padrão.
- **`auth-jwt`**: payload do access token (`sub`, `role`, `exp`) e do refresh, rotas
  `POST /auth/login`, `/auth/refresh`, `/auth/logout` (request/response), formato do
  401/403, dependência de proteção e checagem de `role`.
- **`api-endpoints-protegidos`**: como cada endpoint existente passa a receber e
  filtrar por `usuario_id` (sem quebrar o JSON de resposta atual).
- **`admin-crud`**: rotas administrativas de CRUD de **usuários** e de **transações
  de qualquer usuário**, o guard de admin (role + allowlist `ADMIN_EMAILS` + revalidação
  no banco) e a regra de exclusão de usuário (D-B).
- **`frontend-auth`**: fluxo do modal, armazenamento de access/refresh na sessão,
  envio do `Bearer` pelo `backend_client`, renovação via refresh, proteção e logout.
- **`reorg-agent`**: mapa de movimentação `app/` → `agent/` e pontos de atualização
  (imports, alembic, start.py, pyproject, docs).

## Como verificar

| Requisito | Verificação |
|---|---|
| RF-01 | `pytest` verde; sem imports `app.`; `alembic upgrade head` ok; agente sobe de `agent/` |
| RF-02 | Migration aplicada; inspecionar `usuarios` (unicidade, sem senha em texto) |
| RF-03 | Backfill: nenhuma transação com `usuario_id` nulo; transação nova do agente vinculada |
| RF-04 | Rodar script: cria usuário hasheado; duplicado falha; login funciona com a senha |
| RF-05 | Teste: login ok/401; endpoint sem token → 401; isolamento entre 2 usuários |
| RF-06 | E2E manual: sem login → modal; login → painel próprio; logout → exige login de novo |
| RF-07 | `.env.example` atualizado; subir sem `JWT_SECRET` falha; `start.py` sobe tudo |
| RF-08 | Teste: USER não acessa transação alheia (403/404); rota admin nega USER; admin fora do allowlist → 403 |
| RF-09 | Teste: ADMIN faz CRUD de usuários e de transações de outro usuário; USER recebe 403 |

## Decisões fechadas

- **Login por e-mail.** **Hash bcrypt.** **Access + refresh token** (padrão de mercado).
- Usuário padrão **Jhonatas** (`jhonatas2004@gmail.com`, role `ADMIN`); senha
  fornecida na execução do script. Backfill das transações existentes para ele.
- `responsavel` permanece **campo livre** (quem realizou o gasto ≠ dono da conta).
- Sessão **server-side no Flask** (`HttpOnly`).
- WhatsApp segue **single-user** com a flag atual; **nada novo no agente** agora.
- Campos de `usuarios`: `nome`, `username`, `email`, `senha_hash`, `telefone`,
  `role`, `ativo`, `criado_em`.
- **ADMIN = acesso master:** CRUD completo de usuários e de transações de qualquer
  usuário, com **check extra** (role + allowlist `ADMIN_EMAILS` + revalidação no banco).
- Excluir usuário = **cascade** nas transações dele.
- CRUD admin é **só API** nesta fase (sem tela de administração).

## Dúvidas em aberto

Nenhuma — todas as decisões foram tomadas. Spec pronta para o planejamento.
