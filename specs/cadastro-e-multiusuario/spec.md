# Spec: Cadastro de Usuário + Integração Multi-Usuário no Agente

**Status:** Rascunho
**Feature:** `cadastro-e-multiusuario`

---

## Contexto

Hoje o agente aceita mensagens de **um único número de telefone** fixado em `WHATSAPP_ALLOWED_NUMBER` (env var). Não há tela de cadastro — usuários são criados só via API REST `/admin/usuarios` (autenticada como admin).

Esse conjunto de features resolve os dois pontos:
1. **Tela de cadastro** no dashboard Flask para que um admin crie usuários com nome, e-mail, telefone e senha.
2. **Integração multi-usuário no agente**: o webhook resolve a identidade do remetente pelo telefone do WhatsApp, e todo o processamento (contexto, transações, histórico) é isolado por `usuario_id`.

O modelo `Usuario` já existe (`backend/models/usuario.py`) com campo `telefone` e índice único parcial. O `EstadoStoreRedis` já usa `usuario_id: int` como chave — a estrutura de dados está pronta, falta a integração.

---

## Fora de Escopo

- Auto-cadastro pelo próprio usuário via WhatsApp
- Convite por link (magic link, e-mail de boas-vindas)
- Limitar número de usuários por plano/tier
- OAuth / SSO / login social
- Notificações proativas do agente
- Múltiplas instâncias do agente (uma instância por usuário fica fora do escopo — todos compartilham a mesma instância)

---

## Feature 1 — Tela de Cadastro de Usuário (Dashboard Flask)

### História de usuário

> Como **administrador** do sistema, quero uma tela no dashboard onde possa cadastrar um novo usuário informando nome, e-mail, telefone e senha, para que esse usuário possa usar o agente WhatsApp sem precisar chamar a API diretamente.

### Regras de negócio

| # | Regra |
|---|---|
| RN-01 | Somente usuários com `role = ADMIN` acessam a tela de cadastro |
| RN-02 | E-mail é obrigatório e deve ser único no sistema |
| RN-03 | Telefone é obrigatório para o contexto do agente e deve ser único |
| RN-04 | A senha é hasheada antes de persistida (`bcrypt`, já implementado em `backend/auth/hashing.py`) |
| RN-05 | `username` é gerado automaticamente a partir do e-mail (tudo antes do `@`), sem expor ao admin |
| RN-06 | `role` padrão é `USER`; admin pode promover para `ADMIN` no campo opcional |
| RN-07 | O campo telefone deve aceitar apenas dígitos (sem máscara), ex: `5511999998888` |
| RN-08 | Usuário criado fica `ativo = True` por padrão |

### Fluxo na tela

```
[Formulário de Cadastro]
  Nome *
  E-mail *
  Telefone * (dígitos, ex: 5511999998888)
  Senha *
  [Cadastrar]
        ↓
  POST /admin/usuarios
        ├── 201 → "Usuário cadastrado com sucesso!" + redireciona para lista
        ├── 409 → "Este e-mail já está cadastrado."
        └── 422 → "Dados inválidos: <campo>"
```

### Contrato de API usado (já existente)

```
POST /admin/usuarios
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "nome": "João Silva",
  "username": "<gerado pelo frontend>",
  "email": "joao@exemplo.com",
  "senha": "senhaSegura123",
  "telefone": "5511999998888",
  "role": "USER"
}

201 → { "id": 42, "nome": "...", "email": "...", "telefone": "...", "ativo": true, ... }
409 → { "erro": "Email ja cadastrado" }
```

> `username` será gerado pelo frontend como `email.split("@")[0]` antes de enviar ao endpoint existente. Nenhuma mudança na API é necessária.

### Critérios de aceitação — Feature 1

- [ ] Tela acessível em `/admin/usuarios/novo` (ou equivalente no Flask)
- [ ] Formulário tem os campos: Nome, E-mail, Telefone, Senha (todos obrigatórios)
- [ ] Validação client-side: e-mail com `@`, telefone só dígitos (mín. 10, máx. 15)
- [ ] Envio bem-sucedido exibe mensagem de confirmação e redireciona para lista de usuários
- [ ] E-mail duplicado exibe mensagem de erro sem perder os outros campos preenchidos
- [ ] A rota da tela rejeita usuários não-admin com redirect para login

---

## Feature 2 — Integração Multi-Usuário no Agente

### História de usuário

> Como **usuário cadastrado**, quero poder enviar mensagens para o agente via WhatsApp com meu número pessoal e ter certeza de que apenas meus dados serão acessados e respondidos, independentemente de outros usuários que usem o mesmo agente.

### Visão geral do fluxo novo

```
WhatsApp → Evolution API webhook
                 │
                 ▼
         [Webhook FastAPI]
                 │
          1. Extrair número de telefone (já existe)
          2. Buscar usuario por telefone → BD
                 │
         ┌───────┴────────┐
    Não encontrado     Encontrado + ativo
    ou inativo              │
         │            3. Passar (usuario_id, numero, texto) para a fila
    early return 200        │
                            ▼
                      [Worker]
                            │
                     4. Carregar estado do Redis keyed por usuario_id
                     5. Pipeline: Classificador → Roteador (scoped por usuario_id)
                     6. Gravar histórico no Redis keyed por usuario_id
                     7. Enviar resposta de volta ao número
```

### Regras de negócio

| # | Regra |
|---|---|
| RN-10 | Mensagem de número não cadastrado → discard silencioso (HTTP 200, sem resposta WhatsApp) |
| RN-11 | Mensagem de usuário com `ativo = False` → discard silencioso (HTTP 200) |
| RN-12 | Todas as transações criadas são associadas ao `usuario_id` resolvido no webhook |
| RN-13 | O agente nunca acessa transações de outro `usuario_id` além do resolvido na sessão |
| RN-14 | Histórico de conversa é isolado por `usuario_id` no Redis — chave `estado:{usuario_id}` (já é assim) |
| RN-15 | A env var `WHATSAPP_ALLOWED_NUMBER` é **removida**; a lista de autorizados vem do banco |
| RN-16 | A lookup de usuário por telefone deve ocorrer a cada mensagem (sem cache de telefone→id) |
| RN-17 | Usuários diferentes usando o agente simultaneamente não interferem entre si |

### Passo a passo técnico das mudanças

#### Passo 1 — Novo método no UsuarioRepository

```python
# backend/repositories/usuario_repository.py

async def buscar_por_telefone(self, telefone: str) -> Usuario | None:
    result = await self._session.execute(
        select(Usuario).where(Usuario.telefone == telefone, Usuario.ativo == True)
    )
    return result.scalar_one_or_none()
```

> Telefone normalizado: apenas dígitos, sem `+` ou espaços. Normalizar antes de comparar.

#### Passo 2 — Novo endpoint de resolução de identidade (sob `/auth`, não `/admin`)

**Decisão do usuário (incorporada):** o endpoint de resolução de identidade por telefone **NÃO fica sob `/admin`**. Ele pertence ao domínio de **autenticação/identidade**, então vive sob **`/auth`** (router `backend/controllers/auth.py` ou router de identidade dedicado), separando as *rules* de identidade das *rules* de gestão administrativa. As rotas `/admin/*` continuam exclusivas de gestão (CRUD de usuários).

```
GET /auth/identidade/por-telefone/{telefone}
Authorization: Bearer <token-de-serviço>   ← proteção apropriada de identidade (não a allowlist de admin)

200 → { "id": 42, "nome": "...", "telefone": "...", "ativo": true, ... }
204 → (sem corpo) — usuário não encontrado ou inativo
```

> Telefone normalizado (apenas dígitos) antes da busca. O endpoint reusa `UsuarioRepository.buscar_por_telefone`, que já filtra `ativo = True` — logo inativo e inexistente caem ambos no 204.

**Alternativa sem HTTP (RECOMENDADA e adotada para o webhook):** o agente roda no **mesmo processo** do backend e já tem `session_factory` em `app.state`. Em vez de um HTTP interno, o webhook resolve a identidade **direto** via `UsuarioRepository` (in-process), eliminando latência de uma chamada HTTP do serviço para ele mesmo, evitando um token de serviço extra e simplificando o código e os testes.

> **Decisão tomada:** o **webhook usa a resolução in-process** (chamada direta ao repositório). O **endpoint `/auth/identidade/por-telefone/{telefone}` é criado mesmo assim**, sob `/auth`, para uso administrativo/diagnóstico e para isolar as regras de identidade — mas o caminho quente do webhook não depende dele. Justificativa completa em `plan.md`.

#### Passo 3 — Webhook resolve usuario_id

```python
# agent/entrypoint/webhook.py

async def receber_mensagem(payload: dict, request: Request) -> JSONResponse:
    # ... validações existentes (apikey, event, fromMe, dedup) ...

    numero = extrair_numero(payload)
    texto = extrair_texto(payload)

    # Resolução de identidade
    usuario = await resolver_usuario_por_telefone(request.app.state, numero)
    if usuario is None:
        return JSONResponse(status_code=200, content={"status": "ok"})  # discard silencioso

    await request.app.state.fila.put((usuario.id, numero, texto))
    return JSONResponse(status_code=200, content={"status": "ok"})
```

#### Passo 4 — Worker recebe usuario_id

```python
# agent/entrypoint/worker.py

async def receber(self, usuario_id: int, numero: str, texto: str) -> None: ...

async def _processar(self, usuario_id: int, numero: str, texto: str) -> None:
    agora = datetime.now(timezone.utc)
    estado = await self._estado_store.obter(usuario_id, agora)

    intencao = await self._classificador.classificar(
        mensagem=texto,
        historico=[f"{m.papel}: {m.texto}" for m in estado.historico],
        estado_pendente=resumir_pendencia(estado),
    )

    # Repositório scoped por usuario_id — instanciado por mensagem
    repo = self._repo_factory(usuario_id)

    resultado = await self._roteador.rotear(intencao, usuario_id, agora, {"mensagem": texto}, repo)
    resposta = self._formatador.formatar(resultado)

    await self._estado_store.registrar_mensagem(usuario_id, Mensagem(...), agora)
    await self._evolution.enviar_mensagem(numero, resposta)
```

#### Passo 5 — Repositório escalonado por usuario_id (repo_factory)

Atualmente `_SessionFactoryRepository` em `main.py` tem `usuario_id` fixo. Precisa virar uma factory:

```python
# agent/entrypoint/main.py

def _criar_repo_factory(session_factory) -> Callable[[int], _SessionFactoryRepository]:
    def factory(usuario_id: int) -> _SessionFactoryRepository:
        return _SessionFactoryRepository(session_factory, usuario_id)
    return factory
```

O `Worker` recebe `repo_factory` em vez de um repo fixo. As `Tools` são instanciadas dentro do worker por mensagem (ou recebem `usuario_id` como parâmetro de `executar`).

#### Passo 6 — Roteador passa repo para as Tools

```python
# Opção A: Tools recebem repo como parâmetro de executar (mais testável)
resultado = await tool_listar.executar(params, contexto, repo)

# Opção B: Roteador instancia novas Tools por mensagem com o repo correto
tool_listar = ToolListar(repo=repo, relogio=self._relogio)
resultado = await tool_listar.executar(params, contexto)
```

> Recomendação: **Opção A** — adicionar `repo` como parâmetro de `executar`. Evita instanciar objetos desnecessariamente a cada mensagem.

### Histórico de contexto — design detalhado

O `EstadoStoreRedis` já implementa histórico com:
- `historico: list[Mensagem]` persistido no Redis
- `_MAX_HISTORICO = 5` (últimas 5 mensagens)
- TTL físico de 24h (`_TTL_FISICO_S = 86400`)
- `historico_expira_em` para limpeza por inatividade

**O que falta:**
1. O `Classificador` já aceita `historico: list[str]` mas o `worker._processar` atual não carrega o estado antes de classificar — o histórico está sendo passado vazio.
2. O `Roteador` repassa o histórico ao `ToolConversar`, mas não ao classificador.

**Mudanças necessárias:**
- Worker carrega `estado = await estado_store.obter(usuario_id, agora)` **antes** de classificar
- Passa `[f"{m.papel}: {m.texto}" for m in estado.historico]` ao classificador
- `_MAX_HISTORICO` aumentado de 5 para **10** (configurável via env `HISTORICO_MAX_MENSAGENS`)
- `historico_expira_em` configurável via env `HISTORICO_TTL_HORAS` (padrão: 2h de inatividade)

**Por que não usar LangChain Memory?**

`ConversationBufferMemory` do LangChain assume estado em memória. Para multi-usuário com Redis já configurado, o padrão atual (`EstadoConversa.historico` no Redis) é melhor: é persistido, sobrevive a restart, e já é keyed por `usuario_id`. A integração com LangChain seria adicionar o histórico como contexto no prompt (já é feito no `00-base.md` via `{historico_recente}`) — não há ganho em trocar o mecanismo.

### Isolamento garantido — como verificar

Toda operação de banco de dados passa por `TransacaoRepository` que recebe `usuario_id` como filtro obrigatório. Os métodos já existentes sempre incluem `WHERE usuario_id = :id`. A camada `_SessionFactoryRepository` encapsula isso. Com a `repo_factory` por mensagem, nenhuma query pode vazar dados entre usuários.

| Ponto de isolamento | Mecanismo |
|---|---|
| Transações no banco | `WHERE usuario_id = :id` em todas as queries |
| Estado de conversa no Redis | Chave `estado:{usuario_id}` |
| Histórico de mensagens | Parte do `EstadoConversa`, mesma chave Redis |
| Pendências (confirmação, seleção) | Parte do `EstadoConversa`, mesma chave Redis |

### Critérios de aceitação — Feature 2

**Resolução de identidade:**
- [ ] Mensagem de número não cadastrado → descartada silenciosamente, sem resposta WhatsApp
- [ ] Mensagem de usuário com `ativo = False` → descartada silenciosamente
- [ ] `UsuarioRepository.buscar_por_telefone(telefone)` retorna `None` para inativos
- [ ] `WHATSAPP_ALLOWED_NUMBER` removida de `agent/config.py` e do código

**Isolamento de dados:**
- [ ] Usuário A não consegue ver transações do Usuário B mesmo enviando as mesmas mensagens
- [ ] Cadastrar um gasto como Usuário A → consultar como Usuário B → resposta vazia
- [ ] Histórico de conversa do Usuário A não aparece no contexto do Usuário B

**Histórico de contexto:**
- [ ] Após N mensagens, o classificador recebe as últimas `HISTORICO_MAX_MENSAGENS` no contexto
- [ ] Histórico expira após `HISTORICO_TTL_HORAS` de inatividade (estado limpo)
- [ ] Reiniciar o servidor não perde o histórico (persiste no Redis)

**Endpoint de resolução de identidade (sob `/auth`):**
- [ ] `GET /auth/identidade/por-telefone/{telefone}` retorna 200 com dados ou 204 sem corpo
- [ ] Endpoint exige autenticação apropriada (401/403 sem autorização)
- [ ] O webhook NÃO depende desse endpoint — resolve a identidade in-process via `UsuarioRepository`

**Testes:**
- [ ] `test_webhook.py`: mensagem de número desconhecido → não enfileira nada
- [ ] `test_webhook.py`: mensagem de usuário inativo → não enfileira nada
- [ ] `test_worker.py`: dois usuários processados isoladamente com repos diferentes
- [ ] `test_usuario_repository.py`: `buscar_por_telefone` com usuário ativo, inativo e inexistente

---

## Dependências entre as features

```
Feature 1 (tela de cadastro)
    └── depende de: POST /admin/usuarios (já existe)
    └── depende de: RN-03 — telefone obrigatório (mudança no DTO existente)

Feature 2 (multi-usuário no agente)
    └── depende de: UsuarioRepository.buscar_por_telefone (novo método)
    └── depende de: usuários criados pela Feature 1 (ou via API direta)
    └── NÃO depende de: Feature 1 em produção (pode ser implementada antes)
```

### Mudança no DTO `UsuarioCreateRequest`

`telefone` hoje é `str | None` (opcional). Para o agente funcionar, telefone precisa ser obrigatório. Proposta:

- No **endpoint** `/admin/usuarios`: manter `telefone` opcional (retrocompatibilidade admin via API)
- Na **tela de cadastro**: validar telefone como obrigatório no frontend
- No **agente**: apenas usuários com telefone cadastrado são resolvidos — usuários sem telefone simplesmente nunca terão acesso

> Essa abordagem evita migration e breaking change na API.

---

## Ordem de implementação sugerida

```
Task A — UsuarioRepository.buscar_por_telefone + testes unitários
Task B — GET /auth/identidade/por-telefone/{telefone} endpoint (router de identidade)
Task C — Webhook: substituir WHATSAPP_ALLOWED_NUMBER por lookup no banco
Task D — Worker: receber usuario_id, carregar estado antes de classificar, repo_factory
Task E — Roteador + Tools: receber repo como parâmetro de executar
Task F — Tela de cadastro de usuário no dashboard Flask
```

Tasks A–E são do agente (Python puro); Task F é do dashboard Flask. A e B podem correr em paralelo com F.

---

## Como Verificar

| Requisito | Como testar |
|---|---|
| Resolução por telefone | `pytest tests/test_webhook.py::test_numero_desconhecido_descartado` |
| Isolamento de dados | `pytest tests/test_worker.py::test_dois_usuarios_isolados` |
| buscar_por_telefone | `pytest tests/test_usuario_repository.py::test_buscar_por_telefone` |
| Histórico no Redis | `pytest tests/test_estado_store.py::test_historico_persiste` |
| Tela de cadastro | Acessar `/admin/usuarios/novo` → preencher → verificar usuário no banco |
| Multi-usuário ponta a ponta | Duas contas WhatsApp → cada uma cadastra gastos → consultas isoladas |
