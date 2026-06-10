from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# NullPool é obrigatório: Flask com rotas async executa cada request em um
# event loop novo (via asgiref) e conexões asyncpg ficam presas ao loop em
# que foram criadas. Abre/fecha conexão por request — aceitável para
# dashboard local de usuário único.
engine = create_async_engine(settings.DATABASE_URL, echo=False, poolclass=NullPool)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
