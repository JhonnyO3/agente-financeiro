# Contrato: API JSON de gastos fixos

**Status:** Congelado
**Fronteira:** `backend/controllers/gastos_fixos.py` ↔ `frontend/services/backend_client.py` / `frontend/blueprints/api_proxy.py` / JS

Gastos fixos = transações `recorrente = TRUE` (`parcela_numero = parcela_total = 1`), sem
tabela nova. Mesmas convenções de validação manual, `JSONResponse` por exceção e Decimal
serializado como string.

## `GET /api/gastos-fixos` — listar (RF-03)

Sessão: `get_session`.

### Response 200

```json
{
  "itens": [
    { "id": 12, "descricao": "Claude", "valor": "100.00", "dia_vencimento": 5,
      "data": "2026-06-05", "categoria": "GASTOS_FIXOS",
      "forma_pagamento": "CARTAO_CREDITO", "responsavel": "Jhonatas", "status": "PENDENTE" }
  ],
  "total_mensal": "100.00"
}
```

- Só linhas `recorrente = TRUE` do usuário autenticado, ordenadas por `dia_vencimento`
  (dia de `data`). `total_mensal` = soma dos `valor` em `Decimal`, quantizada `0.01`.
- Lista vazia → `{"itens": [], "total_mensal": "0.00"}`.

## `POST /api/gastos-fixos` — incluir (RF-04)

Sessão: `get_session_begin`. Response **201** `{"id": <int>, "ok": true}`.

### Request (JSON)

| Campo | Tipo | Obrigatório | Default |
|---|---|---|---|
| `descricao` | string | sim | — |
| `valor` | decimal | sim | — |
| `data` | `YYYY-MM-DD` | sim | — |
| `categoria` | `CategoriaEnum` | não | `GASTOS_FIXOS` |
| `forma_pagamento` | `FormaPagamentoEnum` | não | `PIX` |
| `responsavel` | string | não | `"Jhonatas"` |

- Grava `recorrente=True`, `parcela_numero=parcela_total=1`, `grupo_parcela_id=uuid4()`,
  `tipo=GASTO`, `embedding=None`. Status: PIX → `PAGO`; demais → `PENDENTE`
  (regra existente do cadastro).

## `PUT /api/gastos-fixos/{id}` — editar (RF-04)

Sessão: `get_session_begin`. Response 200 `{"ok": true}`.

- Campos editáveis: `descricao`, `valor`, `data`, `categoria`, `forma_pagamento`,
  `responsavel`. Todos opcionais (atualização parcial).
- `404 {"erro": "Gasto fixo nao encontrado"}` se a linha não existe, não é do usuário,
  **ou não é `recorrente = TRUE`**.

## `DELETE /api/gastos-fixos/{id}` — remover (RF-04)

Sessão: `get_session_begin`. Response 200 `{"ok": true}`. Hard delete.
- Mesmas regras de `404` do `PUT` (inclui não-recorrente).

## Erros comuns
| Status | Corpo | Quando |
|---|---|---|
| 400 | `{"erro": "Campos obrigatorios ausentes: ..."}` | falta `descricao`/`valor`/`data` no POST |
| 400 | `{"erro": "..."}` | `valor <= 0`; enums/data inválidos |
| 404 | `{"erro": "Gasto fixo nao encontrado"}` | inexistente / outro usuário / não-recorrente |

## Espelhamento (consumidores)
| Consumidor | Onde |
|---|---|
| `frontend/services/backend_client.py` | `listar_gastos_fixos()`, `criar_gasto_fixo(body)`, `atualizar_gasto_fixo(id, body)`, `excluir_gasto_fixo(id)` |
| `frontend/blueprints/api_proxy.py` | `GET/POST /api/gastos-fixos`, `PUT/DELETE /api/gastos-fixos/<id>` |
| `frontend/static/js/gastos_fixos.js` | payloads/render dos itens e modais |
