# Tarefa 03 — Gastos fixos: service e controller (CRUD)

**Stack:** python
**Depende de:** 02
**Contratos:** `contracts/api-gastos-fixos.md`, `contracts/repositorio-grupos.md`

## Objetivo

Implementar `GET/POST/PUT/DELETE /api/gastos-fixos` sobre as linhas `recorrente = TRUE`
(RF-03/RF-04), sem tabela nova.

## Arquivos (posse exclusiva)

- `backend/services/gastos_fixos.py` (novo)
- `backend/controllers/gastos_fixos.py` (novo)
- `backend/main.py` (somente acrescentar `"gastos_fixos"` a `CONTROLLERS`)
- `tests/backend/test_gastos_fixos.py` (novo)

> Dependência de 02 existe **por causa de `backend/main.py`**: a T02 edita a lista
> `CONTROLLERS` antes; esta tarefa acrescenta `"gastos_fixos"` depois. Não rodar em
> paralelo com a T02.

## Escopo

1. **Service `listar` (RF-03):** `listar_recorrentes(usuario_id)`; ordenar por dia de
   `data`; serializar `id, descricao, valor, dia_vencimento (data.day), data, categoria,
   forma_pagamento, responsavel, status`; `total_mensal` = soma dos `valor` em `Decimal`,
   `str(...quantize("0.01"))`. Vazio → `{"itens": [], "total_mensal": "0.00"}`.
2. **Service `criar` (RF-04):** validar (`descricao`, `valor > 0`, `data`); defaults
   categoria `GASTOS_FIXOS`, forma `PIX`, responsável `"Jhonatas"`; gravar `recorrente=True`,
   `parcela_numero=parcela_total=1`, `grupo_parcela_id=uuid4()`, `tipo=GASTO`,
   `embedding=None`; status PIX→PAGO senão PENDENTE.
3. **Service `atualizar`/`excluir` (RF-04):** carregar com `buscar_por_id(id, usuario_id)`;
   `404` (`NaoEncontradaError`) se ausente, de outro usuário **ou** `recorrente` falso.
   `atualizar` aceita `descricao/valor/data/categoria/forma_pagamento/responsavel`
   (parcial); `excluir` faz hard delete.
4. **Controller `gastos_fixos.py`:** `GET` (`get_session`), `POST` (201, `get_session_begin`),
   `PUT`/`DELETE` (`get_session_begin`); `ValidacaoError`→400, `NaoEncontradaError`→404.
5. **Registro:** acrescentar `"gastos_fixos"` à lista `CONTROLLERS` em `backend/main.py`.

## Critérios de aceite

- [ ] `GET` lista só `recorrente = TRUE` do usuário, ordenado por dia, com `total_mensal` em Decimal
- [ ] Lista vazia → `{"itens": [], "total_mensal": "0.00"}`
- [ ] `POST` cria linha `recorrente=True` 1/1; PIX→PAGO, senão PENDENTE; valor<=0/campo faltando → 400
- [ ] `PUT` altera campos da linha recorrente; `DELETE` faz hard delete
- [ ] `PUT`/`DELETE` em transação não-recorrente ou de outro usuário → 404
- [ ] Testes vermelhos antes (TDD), depois verdes; repositório mockado, `dependency_overrides`

## Verificação local

```bash
uv run pytest tests/backend/test_gastos_fixos.py -v
```
