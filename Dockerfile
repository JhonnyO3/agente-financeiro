FROM python:3.12-slim

# uv (gerenciador de pacotes do projeto)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

# 1) Instala as dependencias primeiro (camada cacheada enquanto o lock nao muda)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Copia o codigo e instala o projeto
COPY . .
RUN uv sync --frozen --no-dev

# venv no PATH -> uvicorn/gunicorn/alembic chamaveis diretamente
ENV PATH="/app/.venv/bin:$PATH"

# Porta default do servico backend; frontend e agente sobrescrevem o
# Start Command (e a porta) no EasyPanel usando ESTA MESMA imagem:
#   backend       -> uvicorn backend.main:app --host 0.0.0.0 --port 8000
#   frontend      -> gunicorn frontend.app:app -b 0.0.0.0:5000 -w 2 --threads 4
#   agente        -> uvicorn agent.entrypoint.main:app --host 0.0.0.0 --port 8001
#
# react-dashboard usa imagem propria (react-dashboard/Dockerfile):
#   docker build -t react-dashboard react-dashboard/
#   docker run -e BACKEND_URL=http://backend:8000 -p 3000:80 react-dashboard
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
