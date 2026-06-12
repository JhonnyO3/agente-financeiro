# Tarefa 09 — Tool Listar

**Stack:** python
**Depende de:** 01, 03, 04
**Contrato:** `resultado-tools.md`, `relogio-contexto.md`

## Objetivo
Agregação determinística (zero LLM) conforme `fluxo-atendimento-lista.md`.

## Arquivos (posse exclusiva)
- `agent/tools/listar.py`
- `tests/test_tool_listar.py`

## Escopo
1. `ToolListar.executar(params, contexto) -> ResultadoTool`:
   - Período ausente → mês atual (via `Relogio`).
   - Filtros (período, categoria, responsável, status) → query/agregação no repository.
   - Agrupar por categoria + subtotais; parcelados (`parcela_total > 1`) na seção visual **PARCELAMENTOS**.
   - Total geral + split pago/pendente em `Decimal`.
   - Sem registros → `status="vazio"`.

## Critérios de aceite
- [ ] Agrupa por categoria com subtotais; PARCELAMENTOS separado.
- [ ] Split pago/pendente e total em `Decimal`; nenhuma chamada LLM.
- [ ] Período vazio → `vazio`.

## Verificação
```bash
uv run pytest tests/test_tool_listar.py -v
```
