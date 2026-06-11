# Tarefa 04 — Auth backend (JWT, guard, hashing)

**Stack:** python
**Depende de:** 02
**Contrato:** `auth-jwt.md`

## Objetivo
Módulo de autenticação: login/refresh/logout, hashing bcrypt, guards `get_usuario_atual`/`get_admin`.

## Arquivos (posse exclusiva)
- `backend/auth/__init__.py`, `backend/auth/jwt.py`, `backend/auth/hashing.py`,
  `backend/auth/dependencies.py`, `backend/auth/refresh_store.py`
- `backend/controllers/auth.py`
- `backend/config.py` (adicionar JWT_SECRET/JWT_ACCESS_EXPIRES_MIN/JWT_REFRESH_EXPIRES_DAYS/ADMIN_EMAILS)
- `tests/backend/test_auth.py`
- adicionar `"auth"` à lista `CONTROLLERS` de `backend/main.py` — **coordenar:** T06 também adiciona `"admin"`. Para evitar colisão em `main.py`, esta tarefa adiciona ambos `"auth","admin"` de uma vez (try/except ImportError já ignora ausente).

## Escopo
1. `jwt.py`: emitir/validar access+refresh HS256 (claims do contrato), rotation.
2. `hashing.py`: `hash_senha`/`verificar_senha` bcrypt.
3. `refresh_store.py`: store in-memory por `jti` com TTL/revogação.
4. `dependencies.py`: `get_usuario_atual` (401), `get_admin` (403 com allowlist + revalidação no banco).
5. `controllers/auth.py`: `/auth/login`, `/auth/refresh`, `/auth/logout`.
6. `config.py`: novas vars obrigatórias (JWT_SECRET sem default).

## Critérios de aceite
- [ ] login ok/401 genérico; refresh rota e revoga; logout idempotente.
- [ ] guard 401 sem Bearer; `get_admin` 403 fora do allowlist/inativo/não-ADMIN.
- [ ] sem `JWT_SECRET` → falha de boot.

## Verificação
```bash
uv run pytest tests/backend/test_auth.py -v
```
