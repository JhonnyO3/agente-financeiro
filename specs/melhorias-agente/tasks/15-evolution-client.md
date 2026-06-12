# Tarefa 15 — Evolution client robusto

**Stack:** python
**Depende de:** 00
**Contrato:** `webhook-fila.md` (consumidor)

## Objetivo
Cliente de envio com `raise_for_status` + retry (envio falho não pode parecer sucesso).

## Arquivos (posse exclusiva)
- `agent/integrations/evolution_client.py`
- `tests/test_evolution_client.py`

## Escopo
1. `enviar_mensagem(numero, texto)` com `raise_for_status` e retry com backoff (sem dep nova: loop com `asyncio.sleep`, já que `tenacity` não está nas deps).
2. Timeout explícito.

## Critérios de aceite
- [ ] HTTP != 2xx → exceção propagada (não silenciada).
- [ ] Retry em 5xx; timeout explícito.

## Verificação
```bash
uv run pytest tests/test_evolution_client.py -v
```
