# Tarefa 02 — Extração v2 (parcela atual, forma, responsável, detalhes, receita)

**Stack:** python · **Dependências:** 01
**Contratos:** `contracts/extracao-v2.md`

## Arquivos que esta tarefa possui
- `app/agents/extrator.py` · `prompts/sistema.md` · `tests/test_agents.py`

## O que implementar
`ExtracaoResult` ganha os campos do contrato (com defaults para retrocompatibilidade).
`prompts/sistema.md` instrui o LLM sobre: parcela atual ("2/4" → atual=2, total=4),
valor da parcela vs total, forma de pagamento (pix/cartão/ausente→OUTRO), responsável
(default Jhonatas), tipo RECEITA ("recebi", "salário", "me pagaram"), e `detalhes`
(frase curta com o contexto extra; mensagem seca → null). `descricao` segue curta.

## Critérios de aceite
- [ ] `ExtracaoResult(**dados_antigos)` constrói sem os campos novos (defaults)
- [ ] Modelo aceita tipo "RECEITA"
- [ ] Testes (mockando o LLM) cobrem os defaults e a presença dos campos novos
- [ ] Prompt cobre todos os exemplos de semântica do contrato

## Verificação
`uv run pytest tests/test_agents.py -v` e suíte completa verde.
