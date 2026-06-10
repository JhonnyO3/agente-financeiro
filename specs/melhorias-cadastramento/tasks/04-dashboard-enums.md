# Tarefa 04 — Dashboard reflete os novos enums

**Stack:** python
**Depende de:** 01
**Contratos:** `contracts/enums.md`

## Objetivo

Atualizar selects e cores do dashboard para o novo conjunto de formas e categorias; remover
qualquer `OUTRO`/`OUTROS` da UI e da API.

## Arquivos (posse exclusiva)

- `dashboard/templates/index.html`
- `dashboard/static/charts.js`
- `dashboard/blueprints/api_transacoes.py`

## Escopo

1. `index.html`: `<option>` de forma de pagamento → `CARTAO_CREDITO, CARTAO_DEBITO, PIX, BOLETO`
   (remover `CARTAO`/`OUTRO`). Selects de categoria → conjunto novo (sem `PARCELAMENTOS`/`OUTROS`,
   com `EDUCACAO`).
2. `charts.js`: `CORES_CATEGORIA` ganha `EDUCACAO`, perde `OUTROS`; fallback ajustado.
3. `api_transacoes.py`: default de `forma_pagamento` deixa de ser `OUTRO` (usar `PIX`);
   validação aceita só os 4 valores.

## Critérios de aceite

- [ ] Nenhum `OUTRO`/`OUTROS`/`CARTAO` (antigo) na UI ou na API
- [ ] `EDUCACAO` aparece nos filtros e tem cor no gráfico
- [ ] POST sem `forma_pagamento` cai em `PIX`

## Verificação local

```bash
uv run pytest tests/ -v -k "dashboard or api" || true
uv run flask --app dashboard.app run --port 5000   # smoke manual
```
