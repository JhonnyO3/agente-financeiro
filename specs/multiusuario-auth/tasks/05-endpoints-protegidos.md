# Tarefa 05 — Endpoints de dados protegidos e filtrados

**Stack:** python
**Depende de:** 03, 04
**Contrato:** `api-endpoints-protegidos.md`

## Objetivo
Aplicar `get_usuario_atual` e filtro por `usuario_id` em todos os controllers/services de dados, sem mudar o JSON.

## Arquivos (posse exclusiva)
- `backend/controllers/{transacoes,resumo,parcelas,graficos,projecao}.py`
- `backend/services/{transacoes,resumo,parcelas,graficos,projecao}.py`
- `tests/backend/test_isolamento_api.py`

## Escopo
1. Cada controller injeta `usuario = Depends(get_usuario_atual)` e passa `usuario.usuario_id` ao service.
2. Services repassam `usuario_id` ao repository; POST ignora body e usa token; PUT/DELETE/grupos de não-dono → 404.
3. `/health` permanece público. Shape JSON inalterado.

## Critérios de aceite
- [ ] Sem Bearer → 401; isolamento entre 2 usuários; shape JSON idêntico ao atual.
- [ ] PUT/DELETE/grupo de id alheio → 404.

## Verificação
```bash
uv run pytest tests/backend/test_isolamento_api.py -v
```
