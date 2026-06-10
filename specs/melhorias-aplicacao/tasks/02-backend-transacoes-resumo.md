# Tarefa 02 — Backend: transações, resumo, parcelas, categorias

**Stack:** python
**Depende de:** 01
**Contratos:** `api-endpoints.md`, `db-engine.md`

## Objetivo

Migrar para FastAPI as rotas de transações (CRUD), resumo, parcelas-ativas e grafico/categorias,
preservando o JSON atual. Lógica em `services/`, controllers finos, schemas em `dtos/`.

## Arquivos (posse exclusiva)

- `backend/controllers/{transacoes,resumo,parcelas}.py`
- `backend/services/{transacoes,resumo,parcelas}.py`
- `backend/dtos/{transacao,resumo}.py`
- `tests/backend/{test_transacoes,test_resumo,test_parcelas}.py`

## Escopo

Reusar `app/repositories/transacao_repository.py` e `app/repositories/dtos.py` (não reimplementar).
Rotas (ver `api-endpoints.md`), formato idêntico ao atual em `dashboard/blueprints/`:
- `GET /api/transacoes` (filtros/paginação), `POST`, `PUT /api/transacoes/{id}`, `DELETE`.
- `GET /api/resumo?periodo`, `GET /api/grafico/categorias?periodo`.
- `GET /api/parcelas-ativas`, `DELETE /api/grupos/{grupo}`.
- Validação `forma_pagamento` (default PIX) e `categoria` por enum; erro ⇒ 400.
- Controllers só chamam services; services usam `get_session`/repo.

## Critérios de aceite

- [ ] Cada rota responde com o mesmo formato do blueprint Flask atual (testes comparam shape)
- [ ] POST sem `forma_pagamento` grava `PIX`; enum inválido ⇒ 400
- [ ] Controllers sem lógica de negócio
- [ ] Reusa `TransacaoRepository`/dtos (sem duplicar)

## Verificação local

```bash
uv run pytest tests/backend/test_transacoes.py tests/backend/test_resumo.py tests/backend/test_parcelas.py -v
```
