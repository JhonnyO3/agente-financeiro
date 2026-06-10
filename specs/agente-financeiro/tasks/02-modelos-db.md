# Tarefa 02 — Modelos de Banco e Migrações

**Stack:** python  
**Depende de:** 01-setup-projeto  
**Arquivos próprios:** `app/models/transacao.py`, `app/models/enums.py`, `migrations/`

## Objetivo

Criar os modelos SQLAlchemy e a migration Alembic que cria a tabela `transacoes` com pgvector.

## Contrato de referência

`contracts/transacao-repository.md` — enums e campos.

## Entregáveis

### `app/models/enums.py`

```python
import enum

class TipoEnum(str, enum.Enum):
    GASTO = "GASTO"
    INVESTIMENTO = "INVESTIMENTO"

class CategoriaEnum(str, enum.Enum):
    ALIMENTACAO = "ALIMENTACAO"
    TRANSPORTE = "TRANSPORTE"
    LAZER = "LAZER"
    INVESTIMENTO = "INVESTIMENTO"
    GASTOS_FIXOS = "GASTOS_FIXOS"
    COMPRAS = "COMPRAS"
```

### `app/models/transacao.py`

Campos conforme `contracts/transacao-repository.md`:
- `id` SERIAL PK
- `tipo` ENUM TipoEnum
- `valor` DECIMAL(12, 2)
- `descricao` TEXT nullable
- `categoria` ENUM CategoriaEnum
- `data` DATE
- `parcela_numero` INTEGER default 1
- `parcela_total` INTEGER default 1
- `grupo_parcela_id` UUID not null (indexed)
- `embedding` VECTOR(1536) nullable
- `criado_em` TIMESTAMP default now()

### Migration Alembic

- `alembic init migrations`
- Migration inicial: `CREATE EXTENSION IF NOT EXISTS vector`, criação da tabela
- Index: `CREATE INDEX ON transacoes USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)`
- Index: `CREATE INDEX ON transacoes (grupo_parcela_id)`
- Index: `CREATE INDEX ON transacoes (data)`

## Critério de aceite

- [ ] `alembic upgrade head` cria a tabela sem erro
- [ ] `SELECT * FROM transacoes LIMIT 1` executa sem erro
- [ ] Extensão `vector` ativa no banco
- [ ] Index de embedding existe (checar com `\d transacoes`)
