# Tarefa 07 — RAG (busca 3 faixas)

**Stack:** python
**Depende de:** 03, 04
**Contrato:** `rag-busca.md`

## Objetivo
`BuscaRAG` que embeda a referência extraída e classifica em MATCH/AMBIGUO/PISO via limiares de Settings.

## Arquivos (posse exclusiva)
- `agent/services/rag.py`
- `tests/test_rag.py`

## Escopo
1. `BuscaRAG.buscar(referencia, usuario_id) -> ResultadoBusca` com `Faixa` e `candidatos`.
2. Embeda **a referência** (não a mensagem crua) via `Embedder`.
3. Consome `buscar_semantico_multiplos_com_distancia` (adapter da T04).
4. Faixas por `RAG_PISO`/`RAG_MARGEM`/`RAG_MAX_OPCOES`.

## Critérios de aceite
- [ ] Texto enviado ao embedder == referência (teste verifica argumento).
- [ ] 1 candidato abaixo do piso com gap ≥ margem → MATCH; 2+ próximos → AMBIGUO; nenhum/abaixo do piso → PISO.
- [ ] Limiares vêm de Settings.

## Verificação
```bash
uv run pytest tests/test_rag.py -v
```
