# Contrato: Fronteira frontend ↔ backend

**Status:** Congelado
**Fronteira:** `frontend/` (Flask :5000) ↔ backend (FastAPI :8000)

## Estratégia: proxy same-origin

O browser continua buscando `/api/*` **na mesma origem** (`:5000`) — `static/{app,charts,table}.js`
NÃO mudam de URL. O frontend Flask expõe rotas `/api/*` que **encaminham** ao backend.

- `frontend/services/backend_client.py`: cliente `httpx` (sync) com `base_url = BACKEND_URL`.
  Métodos por endpoint; sem regra de negócio (só repassa querystring/body e retorna o JSON/status).
- `frontend/blueprints/api_proxy.py` (ou por funcionalidade): rotas `/api/*` que chamam o service
  e devolvem `(json, status_code)` — espelho 1:1 das rotas do backend (`api-endpoints.md`).
- Páginas (`/`) são server-side (Jinja) e podem usar o service para dados iniciais, mas a regra
  é: **view sem lógica de negócio**; o service faz a chamada HTTP.

## Config

`frontend/config.py` (pydantic-settings): `BACKEND_URL` (default `http://localhost:8000`),
`FRONTEND_PORT` (5000). Sem segredos hardcoded.

## Erros

O proxy repassa o status do backend (400/404/500) e o corpo JSON. Timeout do httpx configurável
(default 10s); falha de conexão ⇒ 502 com `{erro: "backend indisponível"}`.
