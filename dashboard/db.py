from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings


class _SessionPorRequest:
    """Cria engine + sessão por chamada, descartando tudo ao final.

    Flask com rotas async executa cada request em um event loop novo (asgiref).
    Um engine compartilhado entre loops quebra: além das conexões asyncpg, o
    próprio engine guarda primitivas asyncio (locks de first-connect) presas ao
    loop do primeiro request. Engine descartável por request elimina qualquer
    estado entre loops — aceitável para dashboard local de usuário único.

    Mantém a interface usada pelos blueprints:
      async with SessionFactory() as session:        # leitura
      async with SessionFactory.begin() as session:  # escrita (auto-commit)
    """

    def __call__(self):
        return self._sessao(comecar_transacao=False)

    def begin(self):
        return self._sessao(comecar_transacao=True)

    @asynccontextmanager
    async def _sessao(self, comecar_transacao: bool):
        engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
        try:
            factory = async_sessionmaker(engine, expire_on_commit=False)
            if comecar_transacao:
                async with factory.begin() as session:
                    yield session
            else:
                async with factory() as session:
                    yield session
        finally:
            await engine.dispose()


SessionFactory = _SessionPorRequest()
