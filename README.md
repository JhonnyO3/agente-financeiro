# Agente Financeiro

Agente financeiro via WhatsApp + dashboard web. Uma mensagem no WhatsApp vira uma
transação categorizada no banco; o dashboard React mostra os números.

```
WhatsApp → Evolution API → agent (FastAPI) ─┐
                                            ├─→ PostgreSQL + pgvector (Railway)
              React dashboard → backend (FastAPI) ─┘
```

- **`backend/`** — API REST (FastAPI) + camada de dados (SQLAlchemy 2.0 async, compartilhada com o agente). Porta **8000**.
- **`react-dashboard/`** — painel web (React + Vite). Porta **5173** em dev, com proxy de `/api`, `/auth` e `/admin` para o backend.
- **`agent/`** — orquestração do WhatsApp (webhook Evolution API, LangChain/OpenAI). Porta **8001**. Não sobe no fluxo de dev do dashboard (depende de Redis + Evolution API).

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/) (gerenciador de pacotes Python — nunca use `pip`/`poetry`)
- Node.js 20+ e npm
- Um PostgreSQL com a extensão **pgvector** (o projeto usa um banco no Railway — ver `.env`)

## Setup (uma vez)

```bash
# 1. Configure o ambiente
cp .env.example .env          # e preencha os valores (DATABASE_URL, OPENAI_API_KEY, JWT_SECRET, ...)

# 2. Dependências Python
uv sync

# 3. Dependências do frontend
npm --prefix react-dashboard install

# 4. (banco novo/vazio) aplique as migrations
uv run alembic upgrade head
```

O `.env` já aponta o `DATABASE_URL` para o banco no Railway
(`postgresql+asyncpg://...@tokaido.proxy.rlwy.net:49412/railway`).

## Subir backend + frontend juntos (dev)

Um único comando sobe o **backend (8000)** e o **frontend React (5173)** ao mesmo tempo,
com logs prefixados (`[backend]` / `[frontend]`) e encerramento conjunto no `Ctrl+C`:

```bash
uv run python start.py
```

- Dashboard: **http://127.0.0.1:5173**
- Backend/health: **http://127.0.0.1:8000/health**

> Use `127.0.0.1`, não `localhost` — evita o atraso de resolução IPv6 (`::1`).

### Alternativa: dois terminais

```bash
# terminal 1 — backend
uv run uvicorn backend.main:app --host 127.0.0.1 --port 8000

# terminal 2 — frontend
npm --prefix react-dashboard run dev
```

### Agente do WhatsApp (opcional, separado)

Depende de Redis e da Evolution API; rode à parte quando precisar:

```bash
uv run uvicorn agent.entrypoint.main:app --host 127.0.0.1 --port 8001
```

## Migrations

```bash
uv run alembic upgrade head                              # aplicar
uv run alembic revision --autogenerate -m "descricao"    # criar nova
```

## Testes

```bash
uv run pytest tests/ -v
```

Todos os testes usam mocks — não tocam banco nem a OpenAI de verdade.

## Deploy

Ver [`DEPLOY.md`](DEPLOY.md) (EasyPanel/Hostinger — mesma imagem para backend e agente,
`react-dashboard/` com imagem própria + nginx).

## Design system

O design system dark que inspira o dashboard está em [`src/`](src/) e documentado em
[`src/README.md`](src/README.md).
