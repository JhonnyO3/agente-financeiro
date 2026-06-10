# Tarefa 06 — API resumo v2 e projeção

**Stack:** python · **Dependências:** 01
**Contratos:** `contracts/api-json-v2.md`, `contracts/modelo-dados.md`

## Arquivos que esta tarefa possui
- `dashboard/blueprints/api_resumo.py` · `dashboard/blueprints/api_projecao.py` (novo)
- `dashboard/app.py` (adicionar `"api_projecao"` à tupla de blueprints)
- `tests/test_dashboard_resumo.py` · `tests/test_dashboard_projecao.py` (novo)

## O que implementar
1. `/api/resumo`: + campo `receitas` (soma `tipo=RECEITA`); `saldo = receitas − gastos`.
   Ajustar os testes existentes do resumo à nova semântica (não deletar cenários).
2. Novo blueprint `api_projecao` (`bp`, prefixo `/api`): `GET /api/projecao` conforme
   contrato — `listar_por_periodo(primeiro_dia_mes_atual, ultimo_dia_mes+5)`, filtrar
   `status == PENDENTE`, agrupar por mês com `Decimal`, sempre 6 elementos (zeros
   quando vazio), label `"Jun/26"`.
3. `/api/grafico/categorias` (mesmo arquivo api_resumo): gastos seguem `tipo=GASTO` —
   conferir que categoria PARCELAMENTOS aparece na pizza naturalmente.

## Critérios de aceite
- [ ] resumo retorna `gastos`, `receitas`, `investimentos`, `saldo` (receitas−gastos)
- [ ] projeção: exatamente 6 meses, só PENDENTEs, `qtd_parcelas` conta parcelados
- [ ] mês sem dados → zeros `"0.00"`, não omitido
- [ ] padrão de teste do projeto (env vars topo, mocks no namespace do blueprint)

## Verificação
`uv run pytest tests/test_dashboard_resumo.py tests/test_dashboard_projecao.py -v` e suíte completa.
