# Tarefa 09 — Frontend: login, sessão, Bearer, refresh, proteção, logout

**Stack:** python
**Depende de:** 04 (contrato `auth-jwt.md` congelado)
**Contrato:** `frontend-auth.md`

## Objetivo
Modal de login, sessão Flask HttpOnly, BackendClient com Bearer + refresh, before_request, logout. Sem cadastro.

## Arquivos (posse exclusiva)
- `frontend/blueprints/auth.py`
- `frontend/services/backend_client.py`
- `frontend/services/sessao.py`
- `frontend/app.py`
- `frontend/config.py` (adicionar `SECRET_KEY` obrigatório)
- `frontend/templates/**` (modal/login)
- `tests/frontend/test_auth.py`

## Escopo
1. `/login` GET/POST (chama `/auth/login`, grava tokens na sessão), `/logout`.
2. `before_request` protege dashboard e `/api/*` (isenta login/logout/estáticos/health).
3. `BackendClient` injeta Bearer por chamada; em 401 tenta `/auth/refresh` 1x, regrava access+refresh, refaz; senão limpa sessão.
4. `SECRET_KEY` obrigatório (boot falha se faltar).

## Critérios de aceite
- [ ] Sem login → modal; login → painel próprio; chamadas levam Bearer.
- [ ] 401 com refresh válido renova transparente; refresh inválido exige login.
- [ ] Logout encerra sessão. Sem cadastro.

## Verificação
```bash
uv run pytest tests/frontend/test_auth.py -v
```
