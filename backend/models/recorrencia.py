import datetime
import decimal

from sqlalchemy import (
    BOOLEAN,
    DATE,
    DECIMAL,
    INTEGER,
    TIMESTAMP,
    VARCHAR,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.enums import CategoriaEnum, FormaPagamentoEnum, TipoEnum
from backend.models.transacao import Base


class Recorrencia(Base):
    __tablename__ = "recorrencias"

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        INTEGER, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    descricao: Mapped[str] = mapped_column(VARCHAR, nullable=False)
    tipo: Mapped[TipoEnum] = mapped_column(String, nullable=False)
    categoria: Mapped[CategoriaEnum] = mapped_column(String, nullable=False)
    valor: Mapped[decimal.Decimal] = mapped_column(DECIMAL(12, 2), nullable=False)
    dia_vencimento: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    forma_pagamento: Mapped[FormaPagamentoEnum | None] = mapped_column(
        VARCHAR, nullable=True
    )
    ativo: Mapped[bool] = mapped_column(
        BOOLEAN, nullable=False, server_default=func.true()
    )
    criado_em: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=False), nullable=True, server_default=func.now()
    )
    encerrado_em: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=False), nullable=True
    )

    __table_args__ = (
        Index("ix_recorrencias_usuario_ativo", "usuario_id", "ativo"),
    )


class RecorrenciaLancamento(Base):
    __tablename__ = "recorrencia_lancamentos"

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=True)
    recorrencia_id: Mapped[int] = mapped_column(
        INTEGER, ForeignKey("recorrencias.id", ondelete="CASCADE"), nullable=False
    )
    competencia: Mapped[datetime.date] = mapped_column(DATE, nullable=False)
    transacao_id: Mapped[int | None] = mapped_column(
        INTEGER, ForeignKey("transacoes.id", ondelete="SET NULL"), nullable=True
    )
    gerado_em: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=False), nullable=True, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "recorrencia_id", "competencia", name="uq_recorrencia_competencia"
        ),
    )
