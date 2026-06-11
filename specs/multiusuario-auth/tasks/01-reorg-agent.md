# Tarefa 01 — Separação de módulos (app/ → backend/ + agent/)

**Stack:** python
**Depende de:** contratos (todos congelados)
**Contrato:** `reorg-agent.md`

## Objetivo
Dividir o antigo `app/` por responsabilidade — camada de dados para `backend/`, orquestração para
`agent/` — e atualizar TODOS os pontos (imports, alembic, start.py, pyproject, testes, docs), sem mudar
comportamento. Bloqueante de toda a feature.

## Arquivos (posse exclusiva)
- move `app/models/**` → `backend/models/**`
- move `app/repositories/{transacao_repository,dtos}.py` → `backend/repositories/**`
- move `app/repositories/database.py` → `agent/db.py` (engine via `agent.config`)
- move resto de `app/**` (entrypoint, agents, services, integrations, config.py) → `agent/**`
- edita: `backend/**` (imports `app.`→`backend.`), `scripts/**`, `migrations/env.py`,
  `migrations/script.py.mako`, `start.py`, `pyproject.toml`, `tests/**`, `CLAUDE.md`, `README.md`

## Escopo
1. Mover models e repositories (transacao_repository, dtos) para `backend/`; `Base` em `backend/models/transacao.py`.
2. Mover o engine helper do agente para `agent/db.py` (usa `agent.config`); repositories continuam recebendo `AsyncSession`.
3. Mover o restante de `app/` para `agent/`.
4. Reescrever imports:
   - agente: dados via `backend.models`/`backend.repositories`; engine via `agent.db`; resto `agent.*`.
   - backend (10 arquivos): `app.models`/`app.repositories` → `backend.models`/`backend.repositories`.
   - scripts: `backend.*` (dados) / `agent.*` (serviços) conforme uso.
5. `migrations/env.py` → `from backend.models.transacao import Base`.
6. `start.py` `AGENTE_CMD` → `agent.entrypoint.main:app`.
7. `pyproject.toml` `packages` → `["agent","backend","frontend"]`.
8. `tests/test_start.py` literal e `tests/frontend/test_isolamento.py` strings → nova estrutura.
9. `CLAUDE.md`, `README.md` → estrutura `backend/`+`agent/`.

## Critérios de aceite
- [ ] Diretório `app/` não existe; `Base` e repositories vivem em `backend/`; agente roda de `agent/`.
- [ ] Agente importa a camada de dados de `backend.*` (in-process).
- [ ] `grep -r "from app"`/`"app\."` sem matches do pacote antigo (código/teste/config).
- [ ] `alembic upgrade head` enxerga a metadata (de `backend.models.transacao`).
- [ ] `start.py` aponta `agent.entrypoint.main:app`.

## Verificação
```bash
uv run pytest tests/ -v
```
