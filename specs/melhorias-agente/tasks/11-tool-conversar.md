# Tarefa 11 — Tool Conversar

**Stack:** python
**Depende de:** 01, 05
**Contrato:** `resultado-tools.md`, `prompts-injection.md`

## Objetivo
Diálogo financeiro **puro** (sem banco), LLM verbaliza via `06-conversar.md`.

## Arquivos (posse exclusiva)
- `agent/tools/conversar.py`
- `tests/test_tool_conversar.py`

## Escopo
1. `ToolConversar.executar(mensagem, historico) -> ResultadoTool` (`acao="conversar"`, `status="concluido"`, `dados={"resposta": ...}`).
2. LLM `Settings.LLM_MODELO_CONVERSAR` via `montar_prompt("conversar", ctx)`.
3. **Não** acessa o repository (sem cálculo/consulta).

## Critérios de aceite
- [ ] Resposta em linguagem natural no `dados.resposta`.
- [ ] Repository nunca é chamado (mock não recebe chamadas).

## Verificação
```bash
uv run pytest tests/test_tool_conversar.py -v
```
