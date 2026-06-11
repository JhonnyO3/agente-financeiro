# Tarefa 06 — CRUD administrativo (só API)

**Stack:** python
**Depende de:** 03, 04
**Contrato:** `admin-crud.md`

## Objetivo
Rotas admin de CRUD de usuários e de transações de qualquer usuário, sob `get_admin`, com cascade.

## Arquivos (posse exclusiva)
- `backend/controllers/admin.py`
- `backend/services/admin_usuarios.py`, `backend/services/admin_transacoes.py`
- `backend/dtos/usuario.py`
- `tests/backend/test_admin.py`

## Escopo
1. `/admin/usuarios` CRUD (sem `senha_hash` nas respostas; email duplicado → 409; reset de senha rehash).
2. `/admin/usuarios/{id}/transacoes` e `/admin/transacoes/{id}` (cross-user, `usuario_id` explícito ou None).
3. DELETE usuário → cascade nas transações.
4. Não tocar `main.py` (lista `CONTROLLERS` já recebe `"admin"` em T04).

## Critérios de aceite
- [ ] ADMIN CRUD usuários e transações de outro usuário; USER → 403; fora do allowlist → 403.
- [ ] Excluir usuário faz cascade; respostas sem `senha_hash`.

## Verificação
```bash
uv run pytest tests/backend/test_admin.py -v
```
