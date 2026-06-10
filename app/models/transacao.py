import datetime
import decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import DATE, DECIMAL, INTEGER, TEXT, TIMESTAMP, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.enums import CategoriaEnum, TipoEnum


class Base(DeclarativeBase):
    pass


class Transacao(Base):
    __tablename__ = "transacoes"

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=True)
    tipo: Mapped[TipoEnum] = mapped_column(String, nullable=False)
    valor: Mapped[decimal.Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    descricao: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    categoria: Mapped[CategoriaEnum] = mapped_column(String, nullable=False)
    data: Mapped[datetime.date] = mapped_column(DATE, nullable=False)
    parcela_numero: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    parcela_total: Mapped[int] = mapped_column(INTEGER, nullable=False, default=1)
    grupo_parcela_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    criado_em: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=False), nullable=False, server_default=func.now()
    )
