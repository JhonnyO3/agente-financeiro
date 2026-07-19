import datetime
import decimal

from sqlalchemy import DECIMAL, INTEGER, TIMESTAMP, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.transacao import Base


class Preferencias(Base):
    __tablename__ = "preferencias"

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        INTEGER,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    renda_mensal: Mapped[decimal.Decimal | None] = mapped_column(
        DECIMAL(12, 2), nullable=True
    )
    metas: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )
    atualizado_em: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=False), nullable=False, server_default=func.now()
    )
