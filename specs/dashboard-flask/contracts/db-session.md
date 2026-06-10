# Contrato: DB Session (Dashboard)

**Status:** Congelado
**Usado por:** T01, T02, T03, T04, T05

---

## Descrição

Como o dashboard Flask obtém e usa sessões AsyncSession do SQLAlchemy.

## Módulo: `dashboard/db.py`

`SessionFactory` é um objeto que cria **engine descartável por request**
(`_SessionPorRequest` em `dashboard/db.py`), preservando a interface
`SessionFactory()` / `SessionFactory.begin()` dos blueprints.

**Por que engine por request (e não engine global + NullPool):** Flask com rotas
`async def` executa cada request em um event loop novo (via asgiref). Além das
conexões asyncpg, o próprio engine global guarda primitivas asyncio — o lock de
first-connect (`_exec_w_sync_on_first_run`) fica preso ao loop do primeiro
request e o segundo request morre com `is bound to a different event loop`,
mesmo com `NullPool` (verificado em runtime). Engine criado e `dispose()`ado
dentro do request elimina qualquer estado compartilhado entre loops; aceitável
para dashboard local de usuário único.

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
