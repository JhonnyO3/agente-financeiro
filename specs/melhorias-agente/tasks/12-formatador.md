# Tarefa 12 — Formatador (templates Python)

**Stack:** python
**Depende de:** 01
**Contrato:** `resultado-tools.md`

## Objetivo
`ResultadoTool` → string WhatsApp via templates Python puros (sem LLM), reproduzindo os `fluxo-atendimento-*.md`.

## Arquivos (posse exclusiva)
- `agent/services/formatador.py`
- `tests/test_formatador.py`

## Escopo
1. `Formatador.formatar(resultado: ResultadoTool) -> str` com `match (acao, status)`.
2. Templates: confirmação/realizado de cadastrar; listagem/vazio de listar; confirmação/realizado/ambíguo de atualizar; confirmação/escopo/realizado/ambíguo de excluir; `conversar` (passa a resposta); `menu`; `erro`.
3. Valores formatados em `R$` a partir de `Decimal`; nenhuma decisão de negócio, nenhum recálculo.

## Critérios de aceite
- [ ] Cobre todos os pares (acao, status) do contrato.
- [ ] Saída bate com os templates dos `fluxo-atendimento-*.md` (cards, subtotais, escopo numerado).
- [ ] Zero LLM.

## Verificação
```bash
uv run pytest tests/test_formatador.py -v
```
