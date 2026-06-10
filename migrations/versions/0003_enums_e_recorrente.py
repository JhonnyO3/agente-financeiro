"""enums_e_recorrente

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-10

Adiciona a coluna `recorrente` e ajusta o default de `forma_pagamento` (deixa de ser
OUTRO). A conversão de valores legados de enum (forma e categoria) é feita na 0004.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transacoes",
        sa.Column("recorrente", sa.BOOLEAN(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("transacoes", "forma_pagamento", server_default="PIX")


def downgrade() -> None:
    op.alter_column("transacoes", "forma_pagamento", server_default="OUTRO")
    op.drop_column("transacoes", "recorrente")
