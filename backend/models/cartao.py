import datetime

from sqlalchemy import BOOLEAN, INTEGER, TIMESTAMP, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.transacao import Base


class Cartao(Base):
    __tablename__ = "cartoes"

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(
        INTEGER, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    apelido: Mapped[str] = mapped_column(String, nullable=False)
    dia_fechamento: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    dia_vencimento: Mapped[int | None] = mapped_column(INTEGER, nullable=True)
    cor: Mapped[str | None] = mapped_column(String, nullable=True)
    ativo: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, server_default=func.true())
    criado_em: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=False), nullable=False, server_default=func.now()
    )
