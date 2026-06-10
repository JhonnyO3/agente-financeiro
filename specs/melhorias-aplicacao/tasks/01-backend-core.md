# Tarefa 01 — Backend core (FastAPI + engine pooled)

**Stack:** python
**Depende de:** contratos (todos congelados)
**Contratos:** `db-engine.md`, `api-endpoints.md`

## Objetivo

Esqueleto do backend FastAPI que sobe sozinho, com engine async **pooled** no lifespan, config,
dependência de sessão e log do gargalo. Sem endpoints de negócio (vêm na T02/T03).

## Arquivos (posse exclusiva)

- `backend/__init__.py`, `backend/main.py`, `backend/config.py`, `backend/db.py`, `backend/dependencies.py`
- `tests/backend/__init__.py`, `tests/backend/test_boot.py`

## Escopo

1. `config.py` (pydantic-settings): lê `DATABASE_URL` (reusa o `.env` existente). Não duplica segredos.
2. `db.py`: `create_async_engine(DATABASE_URL)` (pool default, **sem NullPool**) + `async_sessionmaker`.
3. `main.py`: app FastAPI com `lifespan` que cria engine/sessionmaker em `app.state`, faz
   `engine.dispose()` no shutdown, e no startup emite `logging.info` com o gargalo anterior
   (reconexão por request ~2.8s) e a estratégia (pool reusado). Rota `/health` → `{"ok": true}`.
   Registrar routers por **lista fixa** de módulos `backend.controllers.*` ignorando ausentes
   (try/except ImportError), para T02/T03 plugarem sem tocar `main.py`.
4. `dependencies.py`: `get_session()` (Depends) e `get_session_begin()` para escrita, a partir do
   sessionmaker em `app.state`.

## Critérios de aceite

- [ ] `from backend.main import app` importa e o app sobe (TestClient) com `/health` 200
- [ ] Engine criado uma vez no lifespan (não por request); `dispose` no shutdown
- [ ] Log INFO de startup menciona o gargalo e a correção
- [ ] `get_session` entrega sessão do pool

## Verificação local

```bash
uv run pytest tests/backend/test_boot.py -v
```
