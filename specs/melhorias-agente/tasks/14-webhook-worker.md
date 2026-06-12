# Tarefa 14 — Webhook + Worker (auth, dedup, fila, debounce)

**Stack:** python
**Depende de:** 02, 13
**Contrato:** `webhook-fila.md`

## Objetivo
Borda HTTP autenticada + fila por usuário + micro-debounce `\n`, sempre respondendo (inclusive em erro).

## Arquivos (posse exclusiva)
- `agent/entrypoint/webhook.py`
- `agent/entrypoint/worker.py`
- `tests/test_webhook_worker.py`

## Escopo
1. `webhook.py`: auth por header `apikey` (401 se inválido); filtros silenciosos (evento/fromMe/numero/sem texto); dedup por `message_id` (TTL ~10min); enfileira; 200. Não logar payload inteiro.
2. `worker.py`: fila por usuário; micro-debounce `Settings.DEBOUNCE_SEGUNDOS` juntando com `"\n"`; referência da task + lock; chama `Classificador→Roteador→Formatador→EvolutionClient`; registra histórico; `except` envia erro amigável.

## Critérios de aceite
- [ ] `apikey` inválido → 401; duplicada → processa uma vez; fragmentos < 5s → 1 processamento unido por `\n`.
- [ ] Exceção no processamento → usuário recebe mensagem de erro (mock do client chamado).
- [ ] Filtros retornam 200 sem processar.

## Verificação
```bash
uv run pytest tests/test_webhook_worker.py -v
```
