# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest tests/ -v

# Run a single test
uv run pytest tests/test_pipeline.py::test_sem_estado_classificador_chamado -v

# Start the server
uv run uvicorn agent.entrypoint.main:app --reload

# Run migrations
uv run alembic upgrade head

# Create a new migration
uv run alembic revision --autogenerate -m "description"
```

**Package manager:** always use `uv`, never `pip` or `poetry`. The `uv.lock` is committed.

## Architecture

WhatsApp message → Evolution API webhook → FastAPI → 10s debounce → Pipeline → service layer → repository → PostgreSQL + pgvector → response → Evolution API send.

### Layer rules

The codebase is split into three packages: `agent/` (WhatsApp orchestration), `backend/` (data layer + REST API), and `frontend/` (Flask dashboard). The data layer (`backend/models/`, `backend/repositories/`) is shared in-process by the agent.

- `agent/entrypoint/` — HTTP boundary only. No business logic. `webhook.py` filters unauthorized numbers and non-text messages silently (returns 200), then hands off to `debouncer`.
- `agent/services/` — orchestrate agents + repository. All math in `Decimal`, never delegated to LLM.
- `agent/agents/` — LangChain chains against OpenAI. Each chain uses `with_structured_output(PydanticModel)`. Prompts loaded from `prompts/` via `carregar_prompt(nome)`.
- `backend/models/` — SQLAlchemy 2.0 ORM. The declarative `Base` lives in `backend/models/transacao.py`.
- `backend/repositories/` — SQLAlchemy 2.0 async. `TransacaoRepository` takes a single `AsyncSession`; the wiring adapter `_SessionFactoryRepository` in `agent/entrypoint/main.py` wraps it with per-call sessions using `session_factory.begin()` (auto-commit) for writes and `session_factory()` for reads. The agent's engine helper is `agent/db.py` (uses `agent.config`); the backend's is `backend/db.py` (uses `backend.config`).

### Dependency injection

Everything is wired in `agent/entrypoint/main.py` lifespan. No global `Depends()`. Services are stored in `app.state` and accessed via `request.app.state` in the webhook.

### Conversation state machine (`ConfirmacaoState`)

In-memory dict keyed by phone number, TTL = 5 minutes (UTC-aware). Three states:

- `AGUARDAR_PARCELAS` — user mentioned card without specifying installments; pipeline calls `extrator_parcelas` then `executar_com_parcelas_confirmadas`
- `ALTERAR` — pending edit confirmation; pipeline calls `confirmacao_chain` with context `"sim_nao"`
- `EXCLUIR` — pending delete confirmation; context `"escopo_parcela"` when `pergunta_grupo=True`, otherwise `"sim_nao"`

### Semantic search

`text-embedding-3-small` (1536d). Embedding text for storage: `"{tipo} {categoria} {descricao} {dd/mm/yyyy}"` — never includes monetary value. Search embeds the raw user message. L2 distance threshold > 1.0 = "not found" — decided in service, not repository.

### Installments (parcelas)

One `Transacao` row per installment, all sharing the same `grupo_parcela_id` (UUID) and same embedding vector. Value split with `Decimal`, last installment absorbs rounding remainder. Dates offset +30 days each.

### LLM usage

- `gpt-4o-mini` (temp=0): classification, extraction, categorization
- `gpt-4o` (temp=0.3): formatting final responses to the user (`Formatador`)
- Prompts live in `prompts/` — one file per responsibility. `carregar_prompt("nome.md")` reads relative to the project root.

### Database

Single table `transacoes` with pgvector `embedding vector(1536)`, `ivfflat` index. Hard delete only — no soft delete. `grupo_parcela_id` stored as `VARCHAR` (UUID string) in the ORM.

### Tests

All tests use mocks (no real DB or LLM calls). `test_webhook.py` sets required env vars via `os.environ.setdefault` at module level before importing the app. Other test files defer imports inside test functions to avoid settings validation errors.
