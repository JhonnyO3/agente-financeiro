# Tarefa 05 — API CRUD Transações

**Stack:** python
**Dependências:** 01
**Contratos:** `contracts/db-session.md`, `contracts/periodo.md`, `contracts/api-json.md`, `contracts/repository-reuse.md`

---

## Objetivo

Implementar CRUD completo de transações via API (RF-07, RF-08): listagem paginada com filtros, criação manual, edição e remoção.

---

## Arquivos que esta tarefa possui

- `dashboard/blueprints/api_transacoes.py`

---

## O que implementar

### Blueprint `api_transacoes` com prefixo `/api`

#### `GET /api/transacoes`

1. Ler query params: `periodo` (default `mes_atual`), `tipo`, `categoria`, `pagina` (default 1)
2. `listar_por_periodo(inicio, fim)` → lista completa
3. Filtrar em Python:
   - Se `tipo` presente: `t.tipo == tipo`
   - Se `categoria` presente: `t.categoria == categoria`
4. Ordenar: `data DESC, id DESC`
5. Paginar: `por_pagina = 25`, `total = len(filtrada)`, `paginas = ceil(total/25)`
   - `itens = filtrada[(pagina-1)*25 : pagina*25]`
6. Serializar cada transação conforme `contracts/api-json.md`
7. Retornar `{itens, total, pagina, paginas, por_pagina}`

**Serialização de transação:**
```python
def serializar(t) -> dict:
    return {
        "id": t.id,
        "data": t.data.isoformat(),
        "descricao": t.descricao or "",
        "categoria": t.categoria if isinstance(t.categoria, str) else t.categoria.value,
        "valor": str(t.valor),
        "parcela_numero": t.parcela_numero,
        "parcela_total": t.parcela_total,
        "tipo": t.tipo if isinstance(t.tipo, str) else t.tipo.value,
        "grupo_parcela_id": t.grupo_parcela_id,
    }
```

#### `POST /api/transacoes`

1. Ler JSON do body: `data`, `descricao`, `categoria`, `valor`, `tipo`
2. Validar campos obrigatórios: `data`, `valor`, `tipo`, `categoria`; 400 se faltar
   (validar também que `tipo`/`categoria` são valores válidos dos enums e que
   `valor` parseia como `Decimal` — 400 caso contrário)
3. Criar `TransacaoCreate` com:
   - `parcela_numero=1`, `parcela_total=1`
   - `grupo_parcela_id=uuid4()` — o DTO é tipado `UUID`; o repository converte
     para string internamente
   - `embedding=None` (anotação é `list[float]`, mas dataclass não valida e a
     coluna é nullable — ver `contracts/repository-reuse.md`)
4. `criar(transacao)` com `SessionFactory.begin()`
5. Retornar 201 `{"id": novo.id, "ok": true}`

#### `PUT /api/transacoes/<id>`

1. Em um único bloco `SessionFactory.begin()`:
   - `buscar_por_id(id)` — 404 se não encontrado
   - Ler JSON do body: campos opcionais `data`, `descricao`, `categoria`, `valor`
   - Criar `TransacaoUpdate` com apenas os campos presentes
   - `atualizar(id, dados)`
2. Retornar 200 `{"ok": true}`

(`atualizar` no repository não trata id inexistente — o `buscar_por_id` prévio
na mesma sessão é obrigatório.)

#### `DELETE /api/transacoes/<id>`

1. Em um único bloco `SessionFactory.begin()`:
   - `buscar_por_id(id)` — 404 se não encontrado
   - `excluir(id)`
2. Retornar 200 `{"ok": true}`

---

## Critérios de aceite

- [ ] GET lista 25 itens por página corretamente
- [ ] Filtros `tipo` e `categoria` combinados funcionam
- [ ] POST cria registro com `parcela_numero=1`, UUID gerado
- [ ] POST sem campo obrigatório retorna 400
- [ ] PUT atualiza apenas os campos enviados
- [ ] PUT/DELETE com ID inexistente retornam 404
- [ ] DELETE remove permanentemente (hard delete)
- [ ] Valores monetários sempre como string decimal (não float)

---

## Comando de verificação

```bash
curl "http://localhost:5000/api/transacoes?periodo=mes_atual&pagina=1"

curl -X POST "http://localhost:5000/api/transacoes" \
  -H "Content-Type: application/json" \
  -d '{"data":"2026-06-10","descricao":"Teste","categoria":"OUTROS","valor":"50.00","tipo":"GASTO"}'

curl -X PUT "http://localhost:5000/api/transacoes/1" \
  -H "Content-Type: application/json" \
  -d '{"valor":"75.00"}'

curl -X DELETE "http://localhost:5000/api/transacoes/1"
```
