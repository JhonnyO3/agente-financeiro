# Contrato: Endpoints do backend (JSON)

**Status:** Congelado
**Fronteira:** backend FastAPI (`:8000`) ↔ frontend proxy ↔ browser JS

Regra geral: **preservar rotas, métodos e formato de resposta atuais** (fonte: `dashboard/
blueprints/*` no commit base), com os deltas marcados (DELTA). Valores monetários como string
`"123.45"`. Datas de mês como `"Jun/26"`.

## Rotas (inalteradas em path/método)

| Rota | Método | Resposta |
|---|---|---|
| `/api/resumo?periodo=` | GET | `{gastos, receitas, investimentos, saldo, periodo}` (strings money) |
| `/api/grafico/categorias?periodo=` | GET | `[{categoria, total, percentual}]` (só GASTO; `[]` se zero) |
| `/api/grafico/mensal` | GET | `[{mes, <CATEGORIAS_GASTO...>}]` — **DELTA: 13 meses (−6..+6)** |
| `/api/grafico/evolucao` | GET | `[{mes, gastos, investimentos, receitas}]` — **DELTA: +`receitas` e 13 meses** |
| `/api/parcelas-ativas` | GET | igual ao atual (grupos de parcela em aberto) |
| `/api/grupos/<grupo>` | DELETE | igual ao atual (remove grupo; retorno de contagem/status) |
| `/api/projecao` | GET | `[{mes, gastos, receitas, investimentos?, saldo, qtd_parcelas}]` — **DELTA: 13 meses, todas as transações** |
| `/api/transacoes?…filtros` | GET | igual ao atual (lista paginada/filtrada de transações) |
| `/api/transacoes` | POST | igual ao atual (cria; validações de enum, default `PIX`) |
| `/api/transacoes/<id>` | PUT | igual ao atual (edição parcial) |
| `/api/transacoes/<id>` | DELETE | igual ao atual |
| `/health` | GET | `{ok: true}` |

## DELTAS detalhados

- **evolucao** passa a incluir `receitas` (soma de `tipo=RECEITA` no mês) além de `gastos` e
  `investimentos`, e usa a janela de 13 meses (ver `projecao-13-meses.md`).
- **mensal** usa a mesma janela de 13 meses (hoje são 6). `CATEGORIAS_GASTO` = ALIMENTACAO,
  TRANSPORTE, LAZER, EDUCACAO, GASTOS_FIXOS, COMPRAS, GASTOS_PONTUAIS (INVESTIMENTO/RECEITA fora).
- **projecao** passa a 13 meses e soma **todas** as transações do mês (não só `PENDENTE`).
  Mantém os campos atuais; manter `qtd_parcelas`.

## Validação (transacoes)

`forma_pagamento` ∈ {CARTAO_CREDITO, CARTAO_DEBITO, PIX, BOLETO}; ausente ⇒ `PIX`.
`categoria` ∈ enum atual (sem PARCELAMENTOS/OUTROS, com EDUCACAO). Erros de enum ⇒ 400.
