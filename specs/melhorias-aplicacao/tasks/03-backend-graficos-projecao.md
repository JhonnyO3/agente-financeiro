# Tarefa 03 — Backend: gráficos e projeção (13 meses, receitas)

**Stack:** python
**Depende de:** 01
**Contratos:** `api-endpoints.md`, `projecao-13-meses.md`, `db-engine.md`

## Objetivo

Migrar `grafico/mensal`, `grafico/evolucao` e `projecao` para FastAPI com a janela de 13 meses
(−6..+6) e somando **todas** as transações do mês. Evolução ganha a série **receitas**.

## Arquivos (posse exclusiva)

- `backend/controllers/{graficos,projecao}.py`
- `backend/services/{graficos,projecao}.py`
- `backend/services/janela.py` (utilitário `janela_meses`/`ultimo_dia`)
- `backend/dtos/graficos.py`
- `tests/backend/{test_graficos,test_projecao}.py`

## Escopo

- `janela.py`: `janela_meses(hoje)` (13 meses) e `ultimo_dia(mes)` conforme `projecao-13-meses.md`.
- `mensal`: soma por `CATEGORIAS_GASTO` (ALIMENTACAO, TRANSPORTE, LAZER, EDUCACAO, GASTOS_FIXOS,
  COMPRAS, GASTOS_PONTUAIS), 13 meses, todos presentes (zero onde não há).
- `evolucao`: `{mes, gastos, investimentos, receitas}` por mês, 13 meses.
- `projecao`: 13 meses, soma **todas** as transações do mês (não filtrar PENDENTE); manter campos
  atuais (incl. `qtd_parcelas`).
- Reusa `TransacaoRepository.listar_por_periodo`.

## Critérios de aceite

- [ ] `mensal` e `evolucao` retornam exatamente 13 entradas (−6..+6), ordem crescente
- [ ] `evolucao` inclui `receitas` por mês
- [ ] `projecao` soma todas as transações do mês (PAGO+PENDENTE), 13 meses
- [ ] Mês sem dados aparece com `0.00`

## Verificação local

```bash
uv run pytest tests/backend/test_graficos.py tests/backend/test_projecao.py -v
```
