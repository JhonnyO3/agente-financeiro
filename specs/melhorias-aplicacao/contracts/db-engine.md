# Contrato: Engine pooled do backend

**Status:** Congelado
**Fronteira:** `backend/db.py`, `backend/main.py` (lifespan), consumido por todos os services

## Regra

- Um único `AsyncEngine` criado **uma vez** no `lifespan` do FastAPI
  (`create_async_engine(settings.DATABASE_URL)` — pool default `QueuePool`, **sem `NullPool`**).
- `async_sessionmaker(engine, expire_on_commit=False)` guardado no `app.state`.
- Dependência `get_session()` (FastAPI `Depends`) abre uma sessão por request a partir do pool:
  - leitura: `async with session_factory() as session`
  - escrita: `async with session_factory.begin() as session`
- Services recebem um `TransacaoRepository(session)` (reuso de `app/repositories`).
- `engine.dispose()` no shutdown do lifespan.

## Por que pool reusado funciona aqui

uvicorn roda um event loop único e persistente; as conexões asyncpg do pool vivem nesse loop e
são reusadas entre requests. Some o handshake repetido (~2.8s → ~0.4s). O `NullPool`/engine-por-
request do Flask era um contorno do loop-por-request do asgiref — não se aplica ao FastAPI.

## Log de inicialização (RF-01)

No startup, emitir `logging.info` documentando: gargalo anterior (reconexão por request via
NullPool, ~2.8s) e estratégia atual (engine pooled reusado no loop do uvicorn).
