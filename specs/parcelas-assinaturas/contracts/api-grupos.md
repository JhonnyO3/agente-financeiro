# Contrato: API JSON de grupos de parcelas

**Status:** Congelado
**Fronteira:** `backend/controllers/grupos.py` ↔ `frontend/services/backend_client.py` / `frontend/blueprints/api_proxy.py` / JS

Padrão do projeto: validação manual via `body.get(...)`; exceções de service →
`JSONResponse`; `Decimal` serializado como string `"0.01"`-quantizada; auth via
`get_usuario_atual` (isolamento por `usuario.usuario_id`).

## `PUT /api/grupos/{grupo_parcela_id}` — editar grupo (RF-01)

Sessão: `get_session_begin`. Atômico.

### Request (JSON)

| Campo | Tipo | Obrigatório | Efeito |
|---|---|---|---|
| `descricao` | string | sim | aplicado a **todas** as linhas (pagas e pendentes) |
| `valor_parcela` | string/number (decimal) | sim | aplicado às linhas **PENDENTE**; pagas não mudam |
| `proxima_data` | string `YYYY-MM-DD` | sim | data da próxima pendente; seguintes recalculadas `+1 mês`; pagas intactas |
| `parcela_atual` | int ≥ 1 | sim | linhas com `parcela_numero < parcela_atual` → `PAGO`; demais → `PENDENTE` |
| `parcela_total` | int ≥ 1 | sim | aumentar cria linhas no fim; diminuir exclui linhas finais; todas recebem novo `parcela_total` |

### Response 200

```json
{ "ok": true, "grupo_parcela_id": "550e8400-e29b-41d4-a716-446655440000", "parcela_total": 12 }
```

### Erros

| Status | Corpo | Quando |
|---|---|---|
| 400 | `{"erro": "ID inválido"}` | `grupo_parcela_id` malformado |
| 400 | `{"erro": "Campos obrigatorios ausentes: ..."}` | falta `descricao`/`valor_parcela`/`proxima_data`/`parcela_atual`/`parcela_total` |
| 400 | `{"erro": "..."}` (validação) | `valor_parcela <= 0`; `parcela_total < parcela_atual` ou `parcela_total < 1`; data/valor inválidos |
| 404 | `{"erro": "Grupo nao encontrado"}` | grupo inexistente ou de outro usuário |

### Semântica detalhada
- Carrega o grupo com `buscar_por_grupo_com_embedding`. Vazio (após filtro `usuario_id`) → 404.
- Aplica `descricao` a todas; `parcela_total` a todas.
- Define status por `parcela_atual` (`< atual` → PAGO; `>= atual` → PENDENTE).
- `valor_parcela` só nas PENDENTE.
- Recalcula datas das PENDENTE a partir de `proxima_data` via cadeia mensal
  (`datas_do_grupo`/`adicionar_meses`); PAGO intactas.
- `parcela_total` aumentado: cria linhas via `criar_lote` com mesmo `grupo_parcela_id`,
  `valor_parcela`, categoria/forma/responsável/`embedding` copiados de uma linha do grupo,
  datas continuando a cadeia, status PENDENTE.
- `parcela_total` diminuído: `excluir_por_grupo_e_numeros` para `parcela_numero > parcela_total`.

## `POST /api/grupos` — criar parcelamento (RF-02)

Sessão: `get_session_begin`. Response **201**.

### Request (JSON)

| Campo | Tipo | Obrigatório | Default |
|---|---|---|---|
| `descricao` | string | sim | — |
| `valor_parcela` | decimal | sim | — |
| `parcela_total` | int ≥ 2 | sim | — |
| `parcela_atual` | int ≥ 1 | não | 1 |
| `proxima_data` | `YYYY-MM-DD` | sim | — |
| `categoria` | enum `CategoriaEnum` | não | `COMPRAS` |
| `forma_pagamento` | enum `FormaPagamentoEnum` | não | `CARTAO_CREDITO` |
| `responsavel` | string | não | `"Jhonatas"` |

### Response 201

```json
{ "ok": true, "grupo_parcela_id": "…", "parcela_total": 12 }
```

### Comportamento
- Gera `grupo_parcela_id = uuid4()`. Cria `parcela_total` linhas (`criar_lote`), todas com
  `valor_parcela` (sem rateio), `tipo=GASTO`, `recorrente=False`, `embedding=None`.
- Datas via `datas_do_grupo(proxima_data, parcela_atual, parcela_total)`.
- `parcela_numero < parcela_atual` → `PAGO`; demais → `PENDENTE`.

### Erros
| Status | Corpo | Quando |
|---|---|---|
| 400 | `{"erro": "Campos obrigatorios ausentes: ..."}` | falta campo obrigatório |
| 400 | `{"erro": "..."}` | `parcela_total < 2`; `valor_parcela <= 0`; `parcela_atual < 1` ou `> parcela_total`; enums/data inválidos |

## Espelhamento (consumidores)
| Consumidor | Onde |
|---|---|
| `frontend/services/backend_client.py` | `atualizar_grupo(grupo, body)`, `criar_grupo(body)` |
| `frontend/blueprints/api_proxy.py` | `PUT /api/grupos/<grupo>`, `POST /api/grupos` |
| `frontend/static/js/grupos.js` | payloads dos modais editar/novo |
