"""status_forma_responsavel_detalhes

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transacoes",
        sa.Column("status", sa.String(), nullable=False, server_default="PENDENTE"),
    )
    op.add_column(
        "transacoes",
        sa.Column("forma_pagamento", sa.String(), nullable=False, server_default="OUTRO"),
    )
    op.add_column(
        "transacoes",
        sa.Column("responsavel", sa.String(), nullable=False, server_default="Jhonatas"),
    )
    op.add_column(
        "transacoes",
        sa.Column("detalhes", sa.TEXT(), nullable=True),
    )

    op.execute("UPDATE transacoes SET status='PAGO' WHERE data < CURRENT_DATE")


def downgrade() -> None:
    op.drop_column("transacoes", "detalhes")
    op.drop_column("transacoes", "responsavel")
    op.drop_column("transacoes", "forma_pagamento")
    op.drop_column("transacoes", "status")
