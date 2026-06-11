# Contrato: Separação de módulos (`app/` → `backend/` + `agent/`)

**Status:** Congelado
**Fronteira:** estrutura de pacotes — todo o resto (T02..T10) importa de `backend.*` (dados/domínio) e `agent.*` (orquestração)

## Regra

Correção estrutural **sem mudança de comportamento**. O diretório `app/` deixa de existir. Seu conteúdo
é **dividido** por responsabilidade:

- **Camada de dados → `backend/`:** `app/models/**` e os repositories
  (`app/repositories/transacao_repository.py`, `app/repositories/dtos.py`). A `Base` declarativa passa a
  viver em `backend/models/transacao.py`.
- **Orquestração do agente → `agent/`:** `entrypoint/`, `agents/`, `services/`, `integrations/`,
  `config.py`. O engine helper do agente (`app/repositories/database.py`, que usa `app.config`) vira
  `agent/db.py` (usando `agent.config`).

Os repositories permanecem **agnósticos de sessão** (recebem `AsyncSession`); por isso podem viver em
`backend/` e ser consumidos pelo agente **in-process** (`import backend.repositories...`), cada processo
com seu próprio engine (`backend/db.py` no backend; `agent/db.py` no agente).

## Movimentação

| De | Para |
|---|---|
| `app/models/**` (transacao.py, enums.py) | `backend/models/**` |
| `app/repositories/transacao_repository.py`, `app/repositories/dtos.py` | `backend/repositories/**` |
| `app/repositories/database.py` (engine via `app.config`) | `agent/db.py` (engine via `agent.config`) |
| `app/{entrypoint,agents,services,integrations}/**`, `app/config.py` | `agent/**` |

## Pontos a atualizar (exaustivo)

| Local | De | Para |
|---|---|---|
| Imports de dados no agente | `app.models`, `app.repositories.{transacao_repository,dtos}` | `backend.models`, `backend.repositories.{...}` |
| Engine do agente | `app.repositories.database` | `agent.db` |
| Demais imports internos do agente | `app.{config,services,agents,entrypoint,integrations}` | `agent.{...}` |
| `backend/services/*` e `backend/controllers/*` (10 arquivos) | `app.models`, `app.repositories` | `backend.models`, `backend.repositories` |
| `scripts/backfill_parcelas.py`, `scripts/sanitizacao.py` | `app.*` | `backend.*` (dados) / `agent.*` (serviços) conforme uso |
| `migrations/env.py:13` | `from app.models.transacao import Base` | `from backend.models.transacao import Base` |
| `migrations/script.py.mako` (se referenciar `app.`) | `app.` | conforme destino |
| `start.py` (`AGENTE_CMD`) | `app.entrypoint.main:app` | `agent.entrypoint.main:app` |
| `pyproject.toml` | `packages = ["app"]` | `packages = ["agent","backend","frontend"]` |
| `tests/**` imports | `app.*` | `backend.*` / `agent.*` conforme destino |
| `tests/test_start.py` (assert literal) | `"app.entrypoint.main:app"` | `"agent.entrypoint.main:app"` |
| `tests/frontend/test_isolamento.py` (strings) | `app.` / `from app` | o frontend não deve importar `backend`/`agent` de dados — ajustar as strings verificadas para refletir a nova estrutura |
| `CLAUDE.md`, `README.md` | `app/`, `app.` | `backend/`+`agent/` conforme a camada |

## Critérios de aceitação (verificáveis)

- Não existe diretório `app/`.
- `app/models` e os repositories vivem em `backend/`; `Base` em `backend/models/transacao.py`.
- O agente roda de `agent/` e importa a camada de dados de `backend.*` (in-process).
- `grep -r "from app"`/`"app\."` não retorna imports do pacote antigo (código/teste/config).
- `uv run pytest tests/ -v` passa.
- `uv run alembic upgrade head` funciona (metadata a partir de `backend.models.transacao`).
- `start.py` aponta para `agent.entrypoint.main:app`.

## Não faz

- Não move os **use cases/serviços do agente** (cadastrar/alterar/excluir/consultar/marcar_pago/parcelas)
  para o backend — decisão: nesta fase só a **camada de dados** migra. Esses serviços ficam em `agent/`
  e passam a importar `backend.repositories`/`backend.models`.
- Não altera lógica, assinaturas, schema ou comportamento. Qualquer mudança funcional pertence a T02+.
