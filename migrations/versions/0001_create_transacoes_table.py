"""create_transacoes_table

Revision ID: 0001
Revises:
Create Date: 2026-06-09 21:16:27.204353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE transacoes (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR NOT NULL,
            valor DECIMAL(12, 2) NOT NULL,
            descricao TEXT,
            categoria VARCHAR NOT NULL,
            data DATE NOT NULL,
            parcela_numero INTEGER NOT NULL DEFAULT 1,
            parcela_total INTEGER NOT NULL DEFAULT 1,
            grupo_parcela_id UUID NOT NULL,
            embedding vector(1536),
            criado_em TIMESTAMP NOT NULL DEFAULT now()
        )
    """)

    op.execute(
        "CREATE INDEX ON transacoes USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)"
    )
    op.execute("CREATE INDEX ON transacoes (grupo_parcela_id)")
    op.execute("CREATE INDEX ON transacoes (data)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS transacoes")
