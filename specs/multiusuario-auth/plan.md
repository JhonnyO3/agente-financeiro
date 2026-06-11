# Plano Técnico — multiusuario-auth

**Status:** Aprovado
**Spec:** `specs/multiusuario-auth/spec.md` (Aprovada — RF-01..RF-09)
**Contratos:** `reorg-agent.md`, `schema-usuarios.md`, `auth-jwt.md`, `api-endpoints-protegidos.md`, `admin-crud.md`, `frontend-auth.md` (todos Congelados)

## Arquitetura-alvo

**Princípio (correção estrutural):** 3 módulos com responsabilidades nítidas.
`backend/` é o núcleo — **entidades de banco, migrations, repositories** e as APIs. `agent/` é **só
orquestração** do agente. `frontend/` é a interface. A camada de dados (models + repositories) sai do
antigo `app/` e passa a viver em `backend/`; o agente a consome **in-process** (`import backend.*`).

```
backend/    FastAPI (:8000) — NÚCLEO
            models/        entidades ORM (ex-app/models): transacao, enums(+RoleEnum), usuario — Base vive aqui
            repositories/  ex-app/repositories: transacao_repository, usuario_repository, dtos
            db.py          engine pooled do backend (lifespan)
            auth/          jwt, hashing, dependencies (guard), refresh_store
            controllers/   dados + auth + admin
            services/      services de dashboard + admin
            dtos/          schemas Pydantic (+ usuario)
agent/      agente WhatsApp (ex-app/ SEM models/repositories) — SÓ ORQUESTRAÇÃO
            entrypoint/ (webhook, debounce, main), agents/ (chains LLM), services/ (cadastrar, alterar,
            excluir, marcar_pago, consultar, formatador, pipeline, parcelas, confirmacao_state),
            integrations/ (evolution), config.py, db.py (engine do agente via agent.config)
            → importa backend.models e backend.repositories (in-process)
frontend/   Flask (:5000) — modal de login, sessão server-side HttpOnly, BackendClient envia Bearer,
            before_request protege rotas, refresh automático, logout.
migrations/ env.py importa Base de backend.models.transacao; novas migrations: usuarios + usuario_id (3 fases).
scripts/    criar_usuario.py (CLI bcrypt) — importa backend.*; demais scripts importam backend/agent conforme uso.
```

Fluxo de auth: browser → modal `/login` (Flask) → `POST /auth/login` (FastAPI) → access+refresh →
sessão Flask (HttpOnly) → toda chamada do BackendClient leva `Authorization: Bearer <access>` →
guard `get_usuario_atual` valida HS256, injeta `(usuario_id, role)` → service filtra por `usuario_id`.

## Decisões

- **Separação de módulos (T01), bloqueante e sem mudança de comportamento.** O antigo `app/` é
  **dividido**: `app/models/` → `backend/models/`; `app/repositories/{transacao_repository,dtos}.py` →
  `backend/repositories/`; o resto de `app/` → `agent/`. O engine helper do agente
  (`app/repositories/database.py`, via `app.config`) vira `agent/db.py` (via `agent.config`); os
  repositories permanecem agnósticos de sessão (recebem `AsyncSession`). Atualiza TODOS os imports:
  agente passa a `import backend.models`/`backend.repositories` e `agent.*` no resto; backend passa de
  `app.*` a `backend.models`/`backend.repositories`; `migrations/env.py` importa `Base` de
  `backend.models.transacao`; `scripts/*` importam `backend.*`/`agent.*` conforme uso; `start.py`
  aponta `agent.entrypoint.main:app`; `pyproject.toml` `packages=["agent","backend","frontend"]`;
  testes (incl. strings de `test_isolamento.py` e literal em `test_start.py`); `CLAUDE.md`, `README.md`.
  Critério: `grep -r "app\."`/`from app` sem matches do pacote antigo.
- **Migration em 3 fases** (uma revisão ou três, mas a ordem é fixa) para `transacoes.usuario_id` NOT NULL
  sem quebrar dados:
  1. **nullable:** adiciona `usuarios` + `transacoes.usuario_id` (FK `ON DELETE CASCADE`, **nullable**).
  2. **backfill:** garante usuário padrão Jhonatas (`jhonatas2004@gmail.com`, role ADMIN) — `INSERT ... ON CONFLICT DO NOTHING` por email; `UPDATE transacoes SET usuario_id = (id do Jhonatas) WHERE usuario_id IS NULL`.
  3. **not null:** `ALTER COLUMN usuario_id SET NOT NULL`.
  A senha do Jhonatas **não** é definida na migration (hash placeholder/`ativo` ok); a senha real é
  gravada via `scripts/criar_usuario.py` (idempotente por email — atualiza hash se já existir). Decisão:
  migration nunca contém senha; script é a fonte da credencial.
- **Agente obtém o `usuario_id` do usuário padrão no lifespan.** Nova config `AGENTE_USUARIO_EMAIL`
  (default `jhonatas2004@gmail.com`); no startup do agente resolve-se o `usuario_id` por email (1 query)
  e injeta-se nos services de escrita. `TransacaoCreate` ganha campo `usuario_id: int` (obrigatório); o
  agente preenche com o id resolvido. `responsavel` permanece campo livre, separado do `usuario_id`.
- **Guard de auth via `Depends`.** `get_usuario_atual(request) -> UsuarioToken(usuario_id, role, email)`
  decodifica `Authorization: Bearer`, valida HS256/exp; ausente/expirado/inválido → 401. `get_admin`
  empilha sobre `get_usuario_atual` e aplica o check extra (RF-08): role==ADMIN no token **+** email no
  allowlist `ADMIN_EMAILS` **+** revalidação no banco (usuário existe, ainda ADMIN, ativo). Falha → 403.
- **Filtro por usuario_id no repository.** `TransacaoRepository` ganha `usuario_id: int | None` nos
  métodos de leitura/escrita/agregação; `None` ⇒ sem filtro (uso ADMIN-master). Os services do backend
  recebem `usuario_id` do guard e repassam. JSON de resposta atual permanece byte-compatível.
- **Frontend guarda access+refresh na sessão Flask** (cookie assinado HttpOnly via `SECRET_KEY`).
  `BackendClient` deixa de criar `httpx.Client` sem header: cada chamada passa `access` e, em **401**,
  o frontend tenta `POST /auth/refresh` com o `refresh` da sessão, atualiza a sessão e refaz a chamada
  uma vez; se o refresh falhar, limpa sessão e redireciona ao login. `before_request` protege as rotas
  do dashboard e o proxy `/api/*` exceto rotas de auth/estáticos.
- **`main.py` do backend registra routers por lista fixa** (padrão já existente): adicionar `"auth"` e
  `"admin"` à lista `CONTROLLERS`, mantendo o try/except ImportError para tarefas plugarem sem colidir.
- **Falha explícita de config:** `JWT_SECRET` no backend e `SECRET_KEY` no frontend são obrigatórios
  (sem default) — app não sobe se faltarem (RF-07).

## Tarefas (DAG)

| ID | Tarefa | Stack | Depende de | Arquivos (posse exclusiva) |
|----|--------|-------|-----------|------------------|
| 01 | Separação de módulos: `app/models`→`backend/models`, `app/repositories`→`backend/repositories`, resto→`agent/` (imports, alembic, start.py, pyproject, docs, testes) | python | contratos | move `app/models/**`→`backend/models/**`, `app/repositories/{transacao_repository,dtos}.py`→`backend/repositories/**`, `app/repositories/database.py`→`agent/db.py`, resto `app/**`→`agent/**`; edita `backend/**` (imports), `scripts/**`, `migrations/env.py`, `migrations/script.py.mako`, `start.py`, `pyproject.toml`, `tests/**`, `CLAUDE.md`, `README.md` |
| 02 | Schema: ORM `Usuario`+`RoleEnum`, migration 3 fases (usuarios + usuario_id CASCADE + backfill) | python | 01 | `backend/models/usuario.py`, `backend/models/enums.py` (add RoleEnum), `backend/models/transacao.py` (add `usuario_id`), `migrations/versions/<rev>_usuarios.py`, `tests/test_schema_usuarios.py` |
| 03 | Repository: `usuario_id` em `TransacaoRepository`+DTOs+filtros, `UsuarioRepository` | python | 02 | `backend/repositories/transacao_repository.py`, `backend/repositories/dtos.py`, `backend/repositories/usuario_repository.py`, `tests/test_repository_usuario.py` |
| 04 | Auth backend: módulo JWT (login/refresh/logout), guard `get_usuario_atual`/`get_admin`, hashing | python | 02 | `backend/auth/__init__.py`, `backend/auth/jwt.py`, `backend/auth/hashing.py`, `backend/auth/dependencies.py`, `backend/auth/refresh_store.py`, `backend/controllers/auth.py`, `backend/config.py` (add JWT/ADMIN_EMAILS), `tests/backend/test_auth.py` |
| 05 | Endpoints protegidos: guard + filtro usuario_id em todos os controllers/services de dados | python | 03, 04 | `backend/controllers/{transacoes,resumo,parcelas,graficos,projecao}.py`, `backend/services/{transacoes,resumo,parcelas,graficos,projecao}.py`, `tests/backend/test_isolamento_api.py` |
| 06 | Admin CRUD: rotas usuários + transações de qualquer dono, guard admin, cascade | python | 03, 04 | `backend/controllers/admin.py`, `backend/services/admin_usuarios.py`, `backend/services/admin_transacoes.py`, `backend/dtos/usuario.py`, `tests/backend/test_admin.py` |
| 07 | Script `criar_usuario.py` (bcrypt, idempotente por email, role) | python | 02 | `scripts/criar_usuario.py`, `tests/test_criar_usuario.py` |
| 08 | Agente grava `usuario_id` do usuário padrão (resolve por email no lifespan, via `backend.repositories`) | python | 03 | `agent/entrypoint/main.py`, `agent/config.py` (add `AGENTE_USUARIO_EMAIL`), `agent/services/cadastrar.py`, `tests/test_agente_usuario_id.py` |
| 09 | Frontend auth: modal login, sessão, Bearer no BackendClient, refresh, before_request, logout | python | 04 (contrato) | `frontend/blueprints/auth.py`, `frontend/services/backend_client.py`, `frontend/services/sessao.py`, `frontend/app.py`, `frontend/config.py` (add `SECRET_KEY`), `frontend/templates/**` (modal), `tests/frontend/test_auth.py` |
| 10 | Config final + start.py + `.env.example` + docs | python | 05,06,07,08,09 | `.env.example`, `start.py` (revisão final), `README.md` (seção auth) |

DAG (texto):

```
contratos
  → 01 (rename, bloqueante)
       → 02 (schema)
            → 03 (repository)         → 05 (endpoints protegidos)  [+04]
            → 04 (auth backend)       → 05
                                      → 06 (admin crud)            [+03]
            → 07 (script)
            03 → 08 (agente)
       04(contrato) → 09 (frontend, paralelo a 05/06/07/08 — arquivos só de frontend/)
  → 10 (config/start/docs, por último)
```

## Ordem de integração

1. **T01** mergeada e verde primeiro (sem ela tudo colide em imports). `pytest` deve passar com `agent.*`.
2. **T02** (schema/migration) — base de tudo que usa `usuarios`/`usuario_id`.
3. **T03** e **T04** em paralelo (repository × auth backend; arquivos disjuntos).
4. **T07** (script) e **T08** (agente) em paralelo após T02/T03.
5. **T05** (endpoints) após T03+T04; **T06** (admin) após T03+T04 — arquivos disjuntos entre si
   (T05 não cria `admin.py`; T06 não toca os controllers de dados existentes).
6. **T09** (frontend) em paralelo desde que `auth-jwt.md` esteja congelado (só toca `frontend/`).
7. **T10** por último: `.env.example`, ajuste final de `start.py`, docs.
8. Verificação total: `uv run pytest -q` verde; `alembic upgrade head` ok; isolamento entre 2 usuários;
   admin master; allowlist; login/refresh/logout E2E manual no frontend.

## Riscos

- **Separação quebra strings/literais, não só imports** — `test_start.py` afirma `app.entrypoint.main:app`
  (→ `agent.*`), `test_isolamento.py` usa strings de path, `pyproject.toml packages=["app"]`
  (→ `["agent","backend","frontend"]`) e `migrations/env.py:13` (→ `backend.models.transacao`) são fáceis
  de esquecer. Atenção ao **split de imports**: dados vão para `backend.*`, orquestração para `agent.*` —
  cada arquivo do agente pode ter as duas origens. Critério: `grep -r "from app"`/`"app\."` sem matches.
- **NOT NULL antes do backfill** corromperia a migration — a ordem nullable→backfill→not null é obrigatória;
  o backfill depende de existir o usuário padrão (criar na própria migration, sem senha real).
- **Senha do admin na migration** seria vazamento/insegurança — decidido: migration não grava senha; o
  `scripts/criar_usuario.py` é idempotente por email e define/atualiza o hash.
- **`TransacaoCreate` ganhar `usuario_id` obrigatório** quebra chamadores existentes (agente + backend
  admin); T03 deve atualizar todos os call-sites dentro da sua posse ou expor default seguro — atenção a
  colisão com T08 (agente). Mitigação: T03 adiciona o campo e ajusta repository/DTO; T08 ajusta os
  call-sites do agente (`cadastrar.py`); fronteira é o contrato `schema-usuarios.md`.
- **Refresh rotation no frontend** pode entrar em laço se o backend rotacionar e o frontend não persistir
  o novo refresh — `frontend-auth.md` fixa: refresh OK ⇒ regrava access **e** refresh na sessão; 1 retry só.
- **Allowlist + revalidação no banco** adiciona 1 query por rota admin — aceitável (admin é raro). Token
  forjado com role=ADMIN sem email no allowlist deve dar 403 (teste obrigatório).
- **JSON de resposta deve permanecer idêntico** — o filtro por usuario_id não pode alterar o shape atual
  (paridade verificada em `test_isolamento_api.py`).

## Verificação da feature

- `uv run pytest -q` verde (novos testes + testes do agente intactos, agora sob `agent.*`).
- `uv run alembic upgrade head` aplica `usuarios` + `usuario_id` NOT NULL sem órfãos.
- RF-05/08: 2 usuários distintos veem só as próprias transações; sem Bearer → 401; USER em rota admin → 403;
  token role=ADMIN fora do allowlist → 403; admin inativo → 403.
- RF-09: ADMIN faz CRUD de usuários e de transações de outro usuário; excluir usuário faz cascade.
- RF-06: dashboard sem login → modal; login → painel próprio; logout → exige login; chamadas levam Bearer.
- RF-07: subir sem `JWT_SECRET`/`SECRET_KEY` falha explicitamente; `.env.example` documenta as novas vars;
  `uv run python start.py` sobe agente(`agent.entrypoint.main:app`)+backend+frontend.
