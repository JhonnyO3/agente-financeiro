# Contrato: API JSON v2 (deltas sobre `specs/dashboard-flask/contracts/api-json.md`)

**Status:** Congelado
**Usado por:** T06, T07 (produzem), T08, T09 (consomem)

## GET /api/resumo — MUDA

```json
{
  "gastos": "350.00",
  "receitas": "5000.00",
  "investimentos": "500.00",
  "saldo": "4650.00",
  "periodo": "mes_atual"
}
```
- `receitas` = soma `tipo=RECEITA` no período
- **`saldo` passa a ser `receitas − gastos`** (antes era investimentos − gastos)

## GET /api/projecao — NOVO (blueprint `api_projecao`, prefixo `/api`)

Ignora `?periodo`. Sempre 6 meses: corrente + 5.

```json
[
  {
    "mes": "Jun/26",
    "gastos_pendentes": "750.00",
    "receitas_pendentes": "0.00",
    "saldo_projetado": "-750.00",
    "qtd_parcelas": 3
  }
]
```
- Apenas lançamentos `status = PENDENTE` com data dentro do mês
- `saldo_projetado = receitas_pendentes − gastos_pendentes` (string decimal, pode ser negativa)
- `qtd_parcelas` = registros com `parcela_total > 1` no mês
- Label de mês: mesmo formato `"Jun/26"` do gráfico mensal
- Registro em `dashboard/app.py`: adicionar `"api_projecao"` à tupla de blueprints

## GET /api/transacoes — itens ganham campos

```json
{
  "id": 42, "...": "campos atuais...",
  "status": "PENDENTE",
  "forma_pagamento": "CARTAO",
  "responsavel": "Jhonatas",
  "detalhes": "Comprado na promoção da Steam"
}
```
- `detalhes` null → `""` no JSON (mesma regra da descricao)
- Novo query param `status=PAGO|PENDENTE` (combina com tipo/categoria/periodo)

## POST /api/transacoes — body aceita (opcionais)

`status`, `forma_pagamento`, `responsavel`, `detalhes`. Defaults: PENDENTE / OUTRO /
"Jhonatas" / null. Validação: valores fora dos enums → 400.

## PUT /api/transacoes/<id> — body aceita os mesmos 4 campos (parciais)

## Inalterados

`/api/grafico/*` (gastos seguem sendo `tipo=GASTO`, agora incluindo categoria
PARCELAMENTOS naturalmente), `/api/parcelas-ativas`, `DELETE /api/grupos/<id>`,
`DELETE /api/transacoes/<id>`.
