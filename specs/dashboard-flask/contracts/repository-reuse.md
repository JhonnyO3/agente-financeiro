# Contrato: Reuso do Repository

**Status:** Congelado
**Usado por:** T02, T03, T04, T05

---

## Princípio

O dashboard **não modifica** `app/repositories/transacao_repository.py`.
Usa apenas métodos existentes, complementando com lógica Python onde necessário.

---

## Mapeamento endpoint → métodos do repository

| Endpoint | Método(s) do repo | Lógica Python adicional |
|----------|-------------------|------------------------|
| `GET /api/resumo` | `listar_por_periodo(inicio, fim)` | Somar por tipo com `Decimal` |
| `GET /api/grafico/categorias` | `listar_por_periodo(inicio, fim)` | Filtrar `tipo == GASTO`, agregar por categoria com `Decimal`, calcular percentual, filtrar > 0 |
| `GET /api/grafico/mensal` | `listar_por_periodo(6m_inicio, hoje)` | Agrupar por mês e categoria em Python |
| `GET /api/grafico/evolucao` | `listar_por_periodo(2000-01-01, hoje)` | Agrupar por mês em Python |
| `GET /api/parcelas-ativas` | `listar_por_periodo(hoje, 2030-12-31)` | Filtrar parcela_total>1, agrupar por grupo |
| `GET /api/transacoes` | `listar_por_periodo(inicio, fim)` | Filtrar tipo/categoria, paginar em Python |
| `POST /api/transacoes` | `criar(TransacaoCreate)` | Gerar uuid, setar parcela 1/1 |
| `PUT /api/transacoes/<id>` | `buscar_por_id(id)` + `atualizar(id, TransacaoUpdate)` | 404 se não encontrado |
| `DELETE /api/transacoes/<id>` | `buscar_por_id(id)` + `excluir(id)` | 404 se não encontrado |
| `DELETE /api/grupos/<id>` | `excluir_grupo(UUID)` | Converter str → UUID |

---

## Sessão para leitura vs. escrita

```python
# Leitura (GET)
async with SessionFactory() as session:
    repo = TransacaoRepository(session)
    dados = await repo.listar_por_periodo(inicio, fim)

# Escrita (POST, PUT, DELETE)
async with SessionFactory.begin() as session:
    repo = TransacaoRepository(session)
    await repo.criar(...)   # auto-commit no __aexit__
```

---

## Tipos de dados importantes

- `grupo_parcela_id` no modelo ORM é `str`, mas `TransacaoCreate.grupo_parcela_id`
  é tipado `UUID` — passar `uuid4()` direto (o repository converte com `str()`)
- `excluir_grupo` recebe `UUID` — converter: `from uuid import UUID; UUID(grupo_id_str)`
- `valor` é `Decimal` — serializar como `str(valor)` no JSON (nunca `float`)
- `data` é `datetime.date` — serializar como `data.isoformat()` (`"2026-06-10"`)
- `TransacaoCreate.embedding` está anotado `list[float]`, mas dataclass não valida
  em runtime e a coluna é nullable — passar `None` em inserções manuais funciona
  e é o combinado (sem chamada OpenAI no dashboard)
- **Não usar `agregar_por_categoria` para a pizza**: o método agrega TODOS os
  tipos (não filtra `tipo`), então misturaria investimentos com gastos.
  Usar `listar_por_periodo` + agregação em Python filtrando `tipo == GASTO`.

## Limitação conhecida (aceita)

Editar `descricao`/`categoria`/`data` pelo dashboard **não recalcula o embedding**
(`TransacaoUpdate` não tem esse campo). A busca semântica do agente WhatsApp passa
a usar um vetor desatualizado para esse registro. Aceito no MVP — sem OpenAI no
dashboard por decisão de design.

---

## Imports necessários

```python
from app.repositories.transacao_repository import TransacaoRepository
from app.repositories.dtos import TransacaoCreate, TransacaoUpdate
from app.models.enums import TipoEnum, CategoriaEnum
from dashboard.db import SessionFactory
from dashboard.periodo import resolver_periodo
```
