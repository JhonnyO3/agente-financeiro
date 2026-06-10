# Contrato: Schema de `transacoes` (coluna recorrente)

**Status:** Congelado
**Fronteira:** `app/models/transacao.py`, `app/repositories/dtos.py`, `migrations/versions/0003_*.py`

## Nova coluna

| Coluna | Tipo | Nullable | Default | Semântica |
|---|---|---|---|---|
| `recorrente` | BOOLEAN | NOT NULL | `FALSE` | `TRUE` = gasto fixo mensal contínuo (RF-06) |

## Regras de integridade

- `recorrente = TRUE` ⇒ `parcela_numero = 1`, `parcela_total = 1`, sem grupo de parcelas.
- `data` permanece **NOT NULL** mesmo para recorrentes (data-base/início). Não tornar nullable.
- Default de coluna de `forma_pagamento` deixa de ser `OUTRO`. Migration 0003 reescreve o
  `server_default` (ou remove). Valor de aplicação default = `PIX` (definido em código/DTO).

## Migration 0003 (schema)

- `down_revision = '0002'`.
- `upgrade()`: `add_column recorrente BOOLEAN NOT NULL server_default false`;
  ajustar `server_default` de `forma_pagamento` para não-`OUTRO`.
- `downgrade()`: `drop_column recorrente`; restaurar default anterior.
- Não converte dados de enum aqui (isso é a 0004 / RF-08), apenas o schema.

## DTO

`TransacaoCreate` e `TransacaoUpdate` ganham `recorrente: bool = False`. Default de
`forma_pagamento` no `TransacaoCreate` passa de `FormaPagamentoEnum.OUTRO` para
`FormaPagamentoEnum.PIX`.
