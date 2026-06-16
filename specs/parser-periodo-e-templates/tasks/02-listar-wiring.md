# Tarefa 02 — Wiring de `ToolListar` ao parser de período

**Stack:** python
**Depende de:** 01 (parser implementado)
**Contrato:** `contracts/parser-periodo.md`

## Objetivo

Substituir a resolução de período local de `ToolListar` por uma chamada a `parsear_periodo`,
removendo o código duplicado de `agent/tools/listar.py`. Nenhuma mudança no restante do comportamento
de `ToolListar` (filtros, grupos, parcelados, totais).

## Arquivos (posse exclusiva)

- `agent/tools/listar.py`

## Escopo

1. Importar `from agent.services.parser_periodo import parsear_periodo`.
2. Em `ToolListar.executar`, trocar `_resolver_periodo(params.periodo, self._relogio)` por
   `parsear_periodo(params.periodo, self._relogio)`.
3. **Remover** `_resolver_periodo`. Remover `_MESES_PT`, `_MESES_LABEL` e `_primeiro_e_ultimo_dia`
   de `listar.py` (agora vivem no parser) — desde que nada mais no arquivo os use.
4. Não alterar a assinatura pública de `ToolListar` nem o shape de `ResultadoTool`.

## Critérios de aceite → teste

- [ ] `ToolListar.executar` usa `parsear_periodo`; `grep "_resolver_periodo" agent/tools/listar.py` → 0
- [ ] Sem `_MESES_PT`/`_MESES_LABEL`/`_primeiro_e_ultimo_dia` órfãos em `listar.py`
- [ ] `tests/test_tool_listar.py` continua verde (output e tupla de período inalterados)
- [ ] "hoje" via `ToolListar` produz range de um único dia (antes caía no fallback do mês)

## Verificação local

```bash
uv run pytest tests/test_tool_listar.py -v
```
