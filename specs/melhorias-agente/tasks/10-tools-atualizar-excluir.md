# Tarefa 10 — Tools Atualizar e Excluir

**Stack:** python
**Depende de:** 01, 02, 03, 07
**Contrato:** `resultado-tools.md`, `rag-busca.md`, `relogio-contexto.md`

## Objetivo
Atualizar e Excluir sobre RAG (3 faixas), com diff/propagação e escopo de parcelas. Conforme `fluxo-atendimento-atualizar.md` e `fluxo-atendimento-excluir.md`.

## Arquivos (posse exclusiva)
- `agent/tools/atualizar.py`
- `agent/tools/excluir.py`
- `tests/test_tool_atualizar.py`
- `tests/test_tool_excluir.py`

## Escopo
1. **Atualizar**: RAG por referência → MATCH (diff antigo→novo, `aguardando_confirmacao`), AMBIGUO (`aguardando_selecao`), PISO (`nao_encontrado`). Campo ∈ {valor,data} com parcelas futuras → propaga e lista afetadas. Inclui `campo=status` (marcar pago, sem propagação). **Nunca persiste** (payload pendente).
2. **Excluir**: modo individual (RAG; parcelado → `aguardando_escopo` 1=somente este/2=todos) e modo lote (count → `aguardando_confirmacao` com qtd/período). **Nunca persiste.**

## Critérios de aceite
- [ ] Atualizar MATCH gera diff; AMBIGUO gera opções; PISO gera nao_encontrado.
- [ ] Propagação para futuras em valor/data; status não propaga.
- [ ] Excluir parcelado → escopo numerado; lote → count + confirmação.

## Verificação
```bash
uv run pytest tests/test_tool_atualizar.py tests/test_tool_excluir.py -v
```
