# Tarefa 05 — Consultar e Formatador com receitas

**Stack:** python · **Dependências:** 01
**Contratos:** `contracts/modelo-dados.md`

## Arquivos que esta tarefa possui
- `app/services/consultar.py` · `app/services/formatador.py` (se precisar)
- `prompts/resumo.md` · `tests/test_service_consultar.py`

## O que implementar
1. `ResultadoConsulta` ganha `total_receitas: Decimal` e `balanco: Decimal`
   (= receitas − gastos)
2. Nas 4 consultas (mensal/semanal/geral/grupo): receitas = agregados com
   `categoria == CategoriaEnum.RECEITA`; gastos passam a EXCLUIR também RECEITA
   (hoje excluem só INVESTIMENTO)
3. `prompts/resumo.md`: instruir o formatador a citar receitas e balanço quando
   presentes ("Receitas R$ X · Gastos R$ Y · Balanço R$ Z")

## Critérios de aceite
- [ ] Mês com gasto 350, receita 5000, investimento 500 → totais 350/5000/500, balanço 4650
- [ ] Sem receitas → balanço negativo = −gastos; testes antigos ajustados, não deletados
- [ ] Categoria RECEITA nunca somada em total_gastos

## Verificação
`uv run pytest tests/test_service_consultar.py -v` e suíte completa verde.
