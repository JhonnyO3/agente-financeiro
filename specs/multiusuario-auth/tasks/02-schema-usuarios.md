# Tarefa 02 — Schema usuários + usuario_id (migration 3 fases)

**Stack:** python
**Depende de:** 01
**Contrato:** `schema-usuarios.md`

## Objetivo
ORM `Usuario` + `RoleEnum`, coluna `usuario_id` em `transacoes` (FK CASCADE) e migration nullable→backfill→not null.

## Arquivos (posse exclusiva)
- `backend/models/usuario.py`
- `backend/models/enums.py` (adicionar `RoleEnum`)
- `backend/models/transacao.py` (adicionar `usuario_id`)
- `migrations/versions/<rev>_usuarios_e_usuario_id.py`
- `tests/test_schema_usuarios.py`

## Escopo
1. `RoleEnum(str,Enum)`: ADMIN/USER.
2. `Usuario(Base)` conforme DDL do contrato (email único, telefone único parcial, role default USER, ativo, criado_em).
3. `Transacao.usuario_id` NOT NULL, FK `usuarios.id` ON DELETE CASCADE.
4. Migration em 3 fases: cria `usuarios` + coluna nullable; insere Jhonatas (sem senha real, ON CONFLICT email DO NOTHING); backfill UPDATE; SET NOT NULL.

## Critérios de aceite
- [ ] `usuarios` com email único, telefone único parcial, role ADMIN/USER.
- [ ] Após migration, nenhuma `transacoes.usuario_id` nula; coluna NOT NULL + CASCADE.
- [ ] Migration não grava senha utilizável.

## Verificação
```bash
uv run pytest tests/test_schema_usuarios.py -v
```
