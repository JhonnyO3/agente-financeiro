# Contrato: API JSON (Dashboard Flask)

**Status:** Congelado
**Usado por:** T02, T03, T04, T05 (produzem), T07, T08, T09 (consomem via fetch)

---

## Query params comuns

`?periodo=mes_atual&tipo=GASTO&categoria=ALIMENTACAO&pagina=1`

Todos os endpoints GET aceitam `periodo`. Endpoint de transacoes aceita também `tipo` e `categoria`.

---

## GET /api/resumo

**Response 200:**
```json
{
  "gastos": "350.00",
  "investimentos": "500.00",
  "saldo": "150.00",
  "periodo": "mes_atual"
}
```
- Valores como strings decimais (2 casas) — JS formata para exibição
- `saldo = investimentos - gastos` (positivo = verde, negativo = vermelho)

---

## GET /api/grafico/categorias

**Response 200:**
```json
[
  {"categoria": "ALIMENTACAO", "total": "150.00", "percentual": 42.86},
  {"categoria": "TRANSPORTE",  "total": "100.00", "percentual": 28.57},
  {"categoria": "LAZER",       "total": "100.00", "percentual": 28.57}
]
```
- Apenas categorias com `total > 0`
- Apenas `tipo = GASTO`
- `percentual` com 2 casas decimais (float)

---

## GET /api/grafico/mensal

Sempre últimos 6 meses — ignora query param `periodo`.

**Response 200:**
```json
[
  {
    "mes": "Jan/26",
    "ALIMENTACAO": "200.00",
    "TRANSPORTE": "80.00",
    "LAZER": "0.00",
    "GASTOS_FIXOS": "0.00",
    "COMPRAS": "0.00",
    "GASTOS_PONTUAIS": "0.00",
    "OUTROS": "0.00"
  }
]
```
- Array com exatamente 6 elementos em ordem cronológica crescente (mês mais antigo primeiro)
- Todas as **7 categorias de gasto** presentes, mesmo que `"0.00"`:
  `ALIMENTACAO, TRANSPORTE, LAZER, GASTOS_FIXOS, COMPRAS, GASTOS_PONTUAIS, OUTROS`
  (a categoria `INVESTIMENTO` do enum fica de fora — o gráfico é só de gastos)
- Apenas `tipo = GASTO`

---

## GET /api/grafico/evolucao

**Response 200:**
```json
[
  {"mes": "Jan/26", "gastos": "350.00", "investimentos": "500.00"},
  {"mes": "Fev/26", "gastos": "420.00", "investimentos": "0.00"}
]
```
- Apenas meses com pelo menos 1 registro
- Todos os meses com dados, não limitado a 6

---

## GET /api/parcelas-ativas

**Response 200:**
```json
[
  {
    "grupo_parcela_id": "uuid-string",
    "descricao": "iPhone parcelado",
    "valor_parcela": "199.00",
    "parcela_numero": 3,
    "parcela_total": 12,
    "proxima_data": "2026-07-10",
    "pagas": 2
  }
]
```
- `pagas = parcela_numero - 1` (quantas já foram pagas)
- `proxima_data` = data da próxima parcela pendente (data >= hoje)
- Apenas grupos com ao menos 1 parcela com `data >= hoje`
- Ordenado por `proxima_data` crescente

---

## GET /api/transacoes

**Query:** `?periodo=mes_atual&tipo=GASTO&categoria=ALIMENTACAO&pagina=1`

**Response 200:**
```json
{
  "itens": [
    {
      "id": 42,
      "data": "2026-06-09",
      "descricao": "Coxinha",
      "categoria": "ALIMENTACAO",
      "valor": "100.00",
      "parcela_numero": 1,
      "parcela_total": 1,
      "tipo": "GASTO",
      "grupo_parcela_id": "uuid-string"
    }
  ],
  "total": 38,
  "pagina": 1,
  "paginas": 2,
  "por_pagina": 25
}
```
- Ordenado por `data DESC, id DESC`
- `tipo` filter: `GASTO`, `INVESTIMENTO` ou ausente (todos)
- `categoria` filter: valor do enum ou ausente

---

## POST /api/transacoes

**Request body:**
```json
{
  "data": "2026-06-10",
  "descricao": "Mercado",
  "categoria": "ALIMENTACAO",
  "valor": "89.90",
  "tipo": "GASTO"
}
```

**Response 201:**
```json
{"id": 43, "ok": true}
```

- `parcela_numero=1`, `parcela_total=1`, `grupo_parcela_id=uuid4()` gerados em Python
- `embedding=None` (nullable, sem processamento de IA)
- Validação: todos os campos obrigatórios presentes; 400 se faltarem

---

## PUT /api/transacoes/<id>

**Request body (campos opcionais, apenas o que mudar):**
```json
{
  "data": "2026-06-10",
  "descricao": "Mercado Extra",
  "categoria": "ALIMENTACAO",
  "valor": "95.00"
}
```

**Response 200:**
```json
{"ok": true}
```

**Response 404:**
```json
{"erro": "Transacao nao encontrada"}
```

---

## DELETE /api/transacoes/<id>

**Response 200:**
```json
{"ok": true}
```

**Response 404:**
```json
{"erro": "Transacao nao encontrada"}
```

---

## DELETE /api/grupos/<grupo_parcela_id>

**Response 200:**
```json
{"ok": true, "removidos": 12}
```

**Response 404:**
```json
{"erro": "Grupo nao encontrado"}
```

---

## Erros genéricos

```json
{"erro": "mensagem legível"}
```
Status codes: 400 (input inválido), 404 (não encontrado), 500 (erro interno).
