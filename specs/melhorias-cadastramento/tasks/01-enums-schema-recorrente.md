# Tarefa 01 — Enums, coluna `recorrente`, DTOs e migration 0003

**Stack:** python
**Depende de:** —
**Contratos:** `contracts/enums.md`, `contracts/schema-transacoes.md` (ambos Congelados)

## Objetivo

Estabelecer a base: enums finais, coluna `recorrente` e migration de schema. É a fonte dos
contratos; nada de comportamento de agente/dashboard aqui.

## Arquivos (posse exclusiva)

- `app/models/enums.py`
- `app/models/transacao.py`
- `app/repositories/dtos.py`
- `migrations/versions/0003_enums_e_recorrente.py` (novo)

## Escopo

1. `FormaPagamentoEnum` = `CARTAO_CREDITO`, `CARTAO_DEBITO`, `PIX`, `BOLETO` (remove `OUTRO`/`CARTAO`).
2. `CategoriaEnum` = lista do contrato (+`EDUCACAO`, −`PARCELAMENTOS`, −`OUTROS`).
3. `Transacao.recorrente: bool` (BOOLEAN NOT NULL, server_default false). `forma_pagamento`
   server_default deixa de ser `OUTRO`.
4. `TransacaoCreate.recorrente: bool = False`; default de `forma_pagamento` → `PIX`.
   `TransacaoUpdate.recorrente: bool | None = None`.
5. Migration `0003` (`down_revision='0002'`): `add_column recorrente`; ajustar default de
   `forma_pagamento`. `downgrade` reverte.

## Critérios de aceite

- [ ] `FormaPagamentoEnum`/`CategoriaEnum` batem 1:1 com `contracts/enums.md`
- [ ] `Transacao` e DTOs têm `recorrente`; default de forma é `PIX`
- [ ] `uv run alembic upgrade head` e `alembic downgrade -1` rodam sem erro

## Verificação local

```bash
uv run pytest tests/ -v -k "enum or model or dto" || uv run pytest tests/ -v
uv run alembic upgrade head && uv run alembic downgrade -1
```
