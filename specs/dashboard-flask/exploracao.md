# Exploração — Dashboard Flask

## Estrutura relevante do projeto

```
agente-financeiro/
├── app/
│   ├── config.py                  # Settings(BaseSettings) → DATABASE_URL, OPENAI_API_KEY …
│   ├── models/
│   │   ├── transacao.py           # Transacao(Base): 12 colunas + embedding pgvector
│   │   └── enums.py               # TipoEnum, CategoriaEnum (8 valores)
│   └── repositories/
│       ├── database.py            # create_async_engine + async_sessionmaker
│       ├── dtos.py                # TransacaoCreate, TransacaoUpdate, AgregadoCategoria
│       └── transacao_repository.py  # 11 métodos async
├── specs/dashboard-flask/
│   └── spec.md                    # 8 RF + 11 endpoints + critérios de aceite
└── pyproject.toml                 # uv, Python 3.12+, sqlalchemy[asyncio], asyncpg
```

## Modelo Transacao (tabela `transacoes`)

| Coluna | Tipo Python | SQLAlchemy | Nullable |
|--------|-------------|------------|----------|
| id | int | Integer PK autoincrement | não |
| tipo | TipoEnum | String (GASTO/INVESTIMENTO) | não |
| valor | Decimal | DECIMAL(12,2) | não |
| descricao | str | TEXT | sim |
| categoria | CategoriaEnum | String (8 valores) | não |
| data | date | DATE | não |
| parcela_numero | int | Integer | não |
| parcela_total | int | Integer | não |
| grupo_parcela_id | str | UUID string | não |
| embedding | list[float] | VECTOR(1536) | sim |
| criado_em | datetime | TIMESTAMP | não |

## Métodos do repository disponíveis

| Método | Assinatura resumida | Dashboard usa? |
|--------|---------------------|----------------|
| criar | `(TransacaoCreate) → Transacao` | sim (POST) |
| criar_lote | `(list[TransacaoCreate]) → list[Transacao]` | não |
| buscar_por_id | `(int) → Transacao\|None` | sim (PUT/DELETE) |
| buscar_por_grupo | `(UUID) → list[Transacao]` | sim (parcelas-ativas) |
| atualizar | `(int, TransacaoUpdate) → Transacao` | sim (PUT) |
| excluir | `(int) → None` | sim (DELETE) |
| excluir_grupo | `(UUID) → int` | sim (DELETE grupo) |
| excluir_por_filtros | `(date, date, str?) → int` | não |
| contar_por_filtros | `(date, date, str?) → int` | não |
| listar_por_periodo | `(date, date) → list[Transacao]` | sim (base de tudo) |
| agregar_por_categoria | `(date, date) → list[AgregadoCategoria]` | sim (pizza) |

## Estratégia de banco para o Flask

- `DATABASE_URL` importado de `app.config.settings` (asyncpg+postgresql)
- Flask usa rotas `async def` (requer `flask[async]` via uv)
- `async with SessionFactory() as session: repo = TransacaoRepository(session)`
- Nenhuma migration nova necessária — `embedding nullable=True` já existe

## Dependências a adicionar

```toml
"flask[async]>=3.0"   # async routes + anyio
```

## Convenções do projeto a seguir

- Todos os cálculos numéricos em `Decimal` (Python), nunca JS
- Hard delete apenas (sem soft delete)
- `grupo_parcela_id` é UUID string — converter com `str(uuid4())` ao criar manual
- `periodo=tudo` → `date(2000,1,1)` como piso (consistente com o agente)
- Sem auth — dashboard é local/intranet
- `uv run flask --app dashboard.app run --port 5000`

## Riscos identificados

1. `flask[async]` com asyncpg pode precisar de `FLASK_ASYNC_DRIVER` ou configuração extra
2. Paginação em Python (slice de lista) — aceitável para MVP, dados pequenos
3. Gráfico mensal precisa de agrupamento por mês em Python (repository só tem agregação por categoria)
4. Inserção manual via dashboard: `embedding=None` — ok pois coluna já é nullable
