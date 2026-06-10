# Contrato: Enums compartilhados

**Status:** Congelado
**Fronteira:** `app/models/enums.py` ↔ agentes (`Literal`) ↔ dashboard (HTML/JS) ↔ DTOs

Toda camada que referencia esses valores DEVE usar exatamente o conjunto abaixo. Strings
literais (Pydantic `Literal`, `<option value>`, mapas de cor) devem espelhar 1:1.

## FormaPagamentoEnum (RF-01)

```python
class FormaPagamentoEnum(str, enum.Enum):
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    PIX = "PIX"
    BOLETO = "BOLETO"
```

- `OUTRO`/`OUTROS` **não existem**. Nenhum caminho grava esses valores.
- `CARTAO` (antigo) → mapeado para `CARTAO_CREDITO` na migração.

## CategoriaEnum (RF-04)

```python
class CategoriaEnum(str, enum.Enum):
    ALIMENTACAO = "ALIMENTACAO"
    TRANSPORTE = "TRANSPORTE"
    LAZER = "LAZER"
    EDUCACAO = "EDUCACAO"
    GASTOS_FIXOS = "GASTOS_FIXOS"
    COMPRAS = "COMPRAS"
    GASTOS_PONTUAIS = "GASTOS_PONTUAIS"
    INVESTIMENTO = "INVESTIMENTO"
    RECEITA = "RECEITA"
```

- **Adiciona** `EDUCACAO`. **Remove** `PARCELAMENTOS` e `OUTROS`.

## TipoEnum / StatusEnum — inalterados

```python
TipoEnum   = {GASTO, INVESTIMENTO, RECEITA}
StatusEnum = {PAGO, PENDENTE}
```

## Pontos de espelhamento (consumidores)

| Consumidor | Onde |
|---|---|
| `app/agents/extrator.py` | `Literal[...]` de `forma_pagamento` |
| `app/agents/categorizador.py` | `Literal[...]` de `categoria` (sem OUTROS, com EDUCACAO) |
| `dashboard/templates/index.html` | `<option>` de forma de pagamento |
| `dashboard/static/charts.js` | `CORES_CATEGORIA` (chave por categoria) |
| `dashboard/blueprints/api_transacoes.py` | default/validação de `forma_pagamento` |
