# Tarefa 03 — Repository com usuario_id + UsuarioRepository

**Stack:** python
**Depende de:** 02
**Contrato:** `schema-usuarios.md`, `api-endpoints-protegidos.md`

## Objetivo
Adicionar `usuario_id` ao `TransacaoRepository` (filtros) e DTOs; criar `UsuarioRepository`.

## Arquivos (posse exclusiva)
- `backend/repositories/transacao_repository.py`
- `backend/repositories/dtos.py`
- `backend/repositories/usuario_repository.py`
- `tests/test_repository_usuario.py`

## Escopo
1. `TransacaoCreate.usuario_id: int` (obrigatório); `criar/criar_lote` gravam `usuario_id`.
2. Métodos de leitura/escrita/agregação ganham `usuario_id: int | None` (None ⇒ sem filtro).
3. `UsuarioRepository`: `criar`, `buscar_por_id`, `buscar_por_email`, `listar`, `atualizar`, `excluir`.
4. Ajustar call-sites internos do repository (não tocar os services do agente nem os controllers/services de dashboard do backend — pertencem a T05/T08).

## Critérios de aceite
- [ ] Filtro por `usuario_id` isola transações; `None` retorna todas.
- [ ] `UsuarioRepository.buscar_por_email` único; duplicado falha na criação.

## Verificação
```bash
uv run pytest tests/test_repository_usuario.py -v
```
