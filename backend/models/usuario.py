import datetime

from sqlalchemy import BOOLEAN, INTEGER, TEXT, TIMESTAMP, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.enums import RoleEnum
from backend.models.transacao import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(TEXT, nullable=False)
    username: Mapped[str] = mapped_column(TEXT, nullable=False)
    email: Mapped[str] = mapped_column(TEXT, nullable=False, unique=True)
    senha_hash: Mapped[str] = mapped_column(TEXT, nullable=False)
    telefone: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    role: Mapped[RoleEnum] = mapped_column(
        String, nullable=False, server_default=RoleEnum.USER.value
    )
    ativo: Mapped[bool] = mapped_column(BOOLEAN, nullable=False, server_default=func.true())
    criado_em: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=False), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index(
            "ix_usuarios_telefone_unico",
            "telefone",
            unique=True,
            postgresql_where=text("telefone IS NOT NULL"),
        ),
    )
