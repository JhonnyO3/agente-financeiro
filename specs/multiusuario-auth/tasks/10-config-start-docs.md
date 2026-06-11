# Tarefa 10 — Config final, start.py e docs

**Stack:** python
**Depende de:** 05, 06, 07, 08, 09
**Contrato:** `auth-jwt.md`, `frontend-auth.md`, `reorg-agent.md`

## Objetivo
Documentar novas vars, garantir boot, fechar start.py e README.

## Arquivos (posse exclusiva)
- `.env.example`
- `start.py` (revisão final — agente em `agent.entrypoint.main:app`, lê novas configs)
- `README.md` (seção auth/multiusuário)

## Escopo
1. `.env.example`: `JWT_SECRET`, `JWT_ACCESS_EXPIRES_MIN`, `JWT_REFRESH_EXPIRES_DAYS`, `ADMIN_EMAILS`,
   `SECRET_KEY`, `AGENTE_USUARIO_EMAIL` (sem valores reais).
2. Confirmar que faltar `JWT_SECRET`/`SECRET_KEY` derruba o boot.
3. README: como criar admin (`scripts/criar_usuario.py`), login, rotas admin.

## Critérios de aceite
- [ ] `.env.example` documenta todas as novas vars.
- [ ] Subir sem `JWT_SECRET`/`SECRET_KEY` falha explícito.
- [ ] `uv run python start.py` sobe agente+backend+frontend com a nova organização.

## Verificação
```bash
uv run pytest -q
```
