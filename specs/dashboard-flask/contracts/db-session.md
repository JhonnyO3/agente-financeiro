# Contrato: DB Session (Dashboard)

**Status:** Congelado
**Usado por:** T01, T02, T03, T04, T05

---

## Descrição

Como o dashboard Flask obtém e usa sessões AsyncSession do SQLAlchemy.

## Módulo: `dashboard/db.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
```

**`NullPool` é obrigatório.** Flask com rotas `async def` executa cada request em
um event loop novo (via asgiref). Conexões asyncpg ficam presas ao loop em que
foram criadas — com pool padrão, o segundo request falharia com
`got Future attached to a different loop`. `NullPool` abre/fecha conexão por
request; aceitável para dashboard local de usuário único.

## Padrão de uso nos blueprints

```python
from dashboard.db import SessionFactory
from app.repositories.transacao_repository import TransacaoRepository

@bp.route("/api/exemplo")
async def exemplo():
    async with SessionFactory() as session:
        repo = TransacaoRepository(session)
        dados = await repo.listar_por_periodo(inicio, fim)
    return jsonify(...)
```

**Regras:**
- Leituras: `async with SessionFactory() as session` (sem `begin`)
- Escritas (criar, atualizar, excluir): `async with SessionFactory.begin() as session` (auto-commit)
- Nunca reutilizar a sessão entre requests
- Nunca expor a sessão fora do bloco `async with`

## Dependência de instalação

```toml
# pyproject.toml — adicionar:
"flask[async]>=3.0"
```

Sem `flask[async]`, rotas `async def` não funcionam corretamente.
