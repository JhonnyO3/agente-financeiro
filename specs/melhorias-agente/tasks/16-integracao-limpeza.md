# Tarefa 16 — Integração (wiring) + limpeza dos módulos antigos

**Stack:** python
**Depende de:** 13, 14, 15
**Contrato:** todos (consumidor)

## Objetivo
Religar o `main.py` à nova arquitetura, remover os módulos antigos de `agent/` e reescrever/remover os testes antigos de forma consciente. Resultado: árvore sem código morto e suíte verde.

## Arquivos (posse exclusiva)
- `agent/entrypoint/main.py`             # wiring (lifespan): estado_store, relogio, rag, tools, roteador, worker, webhook
- `agent/services/parcelas.py`           # REMOVER (migrou p/ agent/tools/_parcelas.py na T08)
- `agent/services/pipeline.py`           # REMOVER
- `agent/services/confirmacao_state.py`  # REMOVER
- `agent/services/cadastrar.py`          # REMOVER
- `agent/services/alterar.py`            # REMOVER
- `agent/services/excluir.py`            # REMOVER
- `agent/services/marcar_pago.py`        # REMOVER
- `agent/services/consultar.py`          # REMOVER
- `agent/agents/`                        # REMOVER chains antigas (classificador, extrator*, categorizador, filtro_consulta, confirmacao_chain); embedder migra p/ agents_llm ou permanece reexport
- `agent/entrypoint/debounce.py`         # REMOVER (absorvido por worker.py)
- `agent/db.py`                          # REMOVER (código morto)
- `tests/test_pipeline.py`               # REMOVER (substituído por testes por-tool)
- `tests/test_service_cadastrar.py`      # REMOVER
- `tests/test_service_alterar_excluir.py`# REMOVER
- `tests/test_parcelas_helper.py`        # ATUALIZAR import → agent/tools/_parcelas.py
- `tests/test_webhook.py`                # ATUALIZAR p/ nova auth/fila (ou remover se coberto por test_webhook_worker)

> Nota: o `formatador.py` antigo é substituído pela T12 (mesmo caminho, posse da T12) — esta task não o toca. O passthrough do repo vem de `agent/entrypoint/_adapter_repo.py` (T04).

## Escopo
1. Reescrever o lifespan de `main.py` montando: `Relogio`, `EstadoStoreMemoria`, `Embedder`, adapter de repo (T04), `BuscaRAG`, as 5 Tools, `Formatador`, `Classificador`, `Roteador`, `Worker`, `webhook`. Sem `Depends` global; objetos em `app.state`.
2. Remover os módulos listados; garantir nenhum import órfão.
3. Reescrever/remover os testes antigos conscientemente; manter a suíte verde.

## Critérios de aceite
- [ ] `uv run pytest tests/ -v` verde.
- [ ] `grep -r "agent.services.pipeline\|confirmacao_chain\|agent.db\|services.cadastrar\|services.alterar" agent/ tests/` vazio.
- [ ] App sobe: wiring completo no lifespan; 1 worker documentado.

## Verificação
```bash
uv run pytest tests/ -v
grep -rn "agent\.services\.pipeline\|confirmacao_chain\|agent\.db\b\|services\.cadastrar\|services\.alterar\|services\.excluir\|services\.consultar\|services\.marcar_pago\|entrypoint\.debounce" agent/ tests/
```
