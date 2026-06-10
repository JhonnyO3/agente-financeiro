# Tarefa 01 — Setup do Projeto

**Stack:** python  
**Depende de:** —  
**Bloqueado por:** nada  
**Arquivos próprios:** `pyproject.toml`, `docker-compose.yml`, `.env.example`, `app/__init__.py`, `app/config.py`

## Objetivo

Criar a estrutura de diretórios, dependências e configuração base do projeto. Nenhuma lógica de negócio — só o esqueleto que as demais tarefas constroem em cima.

## Entregáveis

### Estrutura de diretórios

```
app/
  entrypoint/
  services/
  repositories/
  models/
  agents/
  config.py
migrations/
tests/
prompts/          (já existe)
```

### Inicialização com `uv`

```bash
uv init agente-financeiro
cd agente-financeiro
uv python pin 3.12
uv add fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic pgvector \
        langchain langchain-openai openai \
        pydantic pydantic-settings httpx python-dotenv
uv add --dev pytest pytest-asyncio
```

O `uv` gera `pyproject.toml` e `uv.lock` automaticamente. Não usar `pip` diretamente.

### `pyproject.toml` — resultado esperado

```toml
[project]
name = "agente-financeiro"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "sqlalchemy[asyncio]>=2.0",
  "asyncpg>=0.29",
  "alembic>=1.13",
  "pgvector>=0.3",
  "langchain>=0.3",
  "langchain-openai>=0.3",
  "openai>=1.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.3",
  "httpx>=0.27",
  "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8", "pytest-asyncio>=0.23"]
```

### `app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    EVOLUTION_API_URL: str
    EVOLUTION_INSTANCE: str
    EVOLUTION_API_KEY: str
    WHATSAPP_ALLOWED_NUMBER: str

    class Config:
        env_file = ".env"

settings = Settings()
```

### `docker-compose.yml`

Sobe apenas PostgreSQL com extensão pgvector:
```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: agente_financeiro
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
```

### `.env.example`

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agente_financeiro
OPENAI_API_KEY=sk-...
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_INSTANCE=minha-instancia
EVOLUTION_API_KEY=sua-chave
WHATSAPP_ALLOWED_NUMBER=5511957818539
```

## Critério de aceite

- [ ] `uv run pytest tests/` executa sem erro de importação
- [ ] `docker compose up -d` sobe o banco sem erro
- [ ] `from app.config import settings` funciona com `.env` preenchido
