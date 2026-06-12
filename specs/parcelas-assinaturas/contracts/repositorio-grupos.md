# Contrato: Métodos de repositório e DTO para grupos/recorrentes

**Status:** Congelado
**Fronteira:** `backend/repositories/transacao_repository.py` + `backend/repositories/dtos.py` ↔ `backend/services/grupos.py`, `backend/services/gastos_fixos.py`

Métodos **novos** no `TransacaoRepository` (a classe existente; mesma assinatura de
construtor `TransacaoRepository(session)`). Os existentes (`buscar_por_grupo`, `criar`,
`criar_lote`, `buscar_por_id`, `atualizar`, `excluir`, `excluir_grupo`) ficam inalterados.

## `buscar_por_grupo_com_embedding`

```python
async def buscar_por_grupo_com_embedding(
    self, grupo_parcela_id: UUID, usuario_id: int | None = None
) -> list[Transacao]: ...
```

- Idêntico a `buscar_por_grupo`, porém com `.options(undefer(Transacao.embedding))` para
  trazer o `embedding` (que é `deferred`) sem disparar query por objeto.
- Ordenado por `Transacao.parcela_numero`. Filtra por `usuario_id` quando informado.

## `listar_recorrentes`

```python
async def listar_recorrentes(self, usuario_id: int) -> list[Transacao]: ...
```

- `select(Transacao).where(Transacao.recorrente == True, Transacao.usuario_id == usuario_id)`.
- Ordenado por `Transacao.data`. `usuario_id` **obrigatório** (isolamento).

## `excluir_por_grupo_e_numeros`

```python
async def excluir_por_grupo_e_numeros(
    self, grupo_parcela_id: UUID, numeros: list[int], usuario_id: int | None = None
) -> int: ...
```

- `delete(Transacao)` onde `grupo_parcela_id == str(gid)` **e** `parcela_numero IN numeros`.
- Filtra por `usuario_id` quando informado. Faz `flush`. Retorna `rowcount`. Usado ao
  diminuir o total de parcelas (RF-01).

## Mutação em lote (sem método dedicado)

A edição de título/valor/data/status/`parcela_total`/`parcela_numero` das linhas existentes
do grupo é feita pelo **service**, mutando os atributos dos objetos ORM retornados por
`buscar_por_grupo_com_embedding` dentro da sessão `get_session_begin` (commit/rollback
automático). **`TransacaoUpdate` não é estendido**; o método genérico `atualizar` não é
usado para grupos.

## DTO

Nenhum DTO novo. `TransacaoCreate` (já existente) é usado por `criar_lote` para as linhas
novas, com `embedding` copiado do grupo (ou `None` na criação via `POST /api/grupos`).
