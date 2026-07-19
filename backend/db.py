from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)


def criar_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True, pool_recycle=1800)


def criar_sessionmaker(engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)
