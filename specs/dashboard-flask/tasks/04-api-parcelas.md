# Tarefa 04 — API Parcelas Ativas

**Stack:** python
**Dependências:** 01
**Contratos:** `contracts/db-session.md`, `contracts/api-json.md`, `contracts/repository-reuse.md`

---

## Objetivo

Implementar os endpoints de parcelas em andamento (RF-06): listar grupos com parcelas futuras e excluir um grupo inteiro.

---

## Arquivos que esta tarefa possui

- `dashboard/blueprints/api_parcelas.py`

---

## O que implementar

### Blueprint `api_parcelas` com prefixo `/api`

#### `GET /api/parcelas-ativas`

1. Buscar todas as transações com `data >= date.today()`:
   - `listar_por_periodo(date.today(), date(2030, 12, 31))` (range futuro amplo)
2. Filtrar: `parcela_total > 1` (é parcelado)
3. Agrupar por `grupo_parcela_id`
4. Para cada grupo, determinar:
   - `descricao`: descricao da primeira transação do grupo
   - `valor_parcela`: valor de qualquer parcela do grupo (todas iguais)
   - `parcela_numero`: o menor número de parcela pendente (data >= hoje)
   - `parcela_total`: total de parcelas
   - `proxima_data`: data da parcela com menor número no grupo
   - `pagas`: `min(parcela_numero no grupo futuro) - 1`
5. Ordenar por `proxima_data` crescente
6. Retornar conforme `contracts/api-json.md`

#### `DELETE /api/grupos/<grupo_parcela_id>`

1. `excluir_grupo(UUID(grupo_parcela_id))` — lembrar de converter `str → UUID`
2. Se `rowcount == 0`: retornar 404
3. Retornar `{"ok": true, "removidos": rowcount}`

**Tratamento de erro na conversão UUID:**
```python
from uuid import UUID
try:
    gid = UUID(grupo_parcela_id)
except ValueError:
    return jsonify({"erro": "ID inválido"}), 400
```

---

## Critérios de aceite

- [ ] `GET /api/parcelas-ativas` retorna apenas transações com `data >= hoje`
- [ ] Transações à vista (`parcela_total == 1`) não aparecem
- [ ] Campo `pagas` reflete quantas parcelas passadas existem no grupo
- [ ] `DELETE /api/grupos/<id>` remove todos os registros do grupo
- [ ] `DELETE` de grupo inexistente retorna 404
- [ ] UUID inválido na URL retorna 400

---

## Comando de verificação

```bash
curl "http://localhost:5000/api/parcelas-ativas"
# Esperar lista de grupos parcelados com data futura

curl -X DELETE "http://localhost:5000/api/grupos/uuid-aqui"
# Esperar {"ok": true, "removidos": N}
```
