"""preferencias

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-18

Cria a tabela `preferencias`, 1 linha por usuario (UNIQUE em usuario_id, FK CASCADE),
com renda mensal informativa e o mapa de metas por categoria em JSONB.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS preferencias (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL UNIQUE
                REFERENCES usuarios(id) ON DELETE CASCADE,
            renda_mensal DECIMAL(12, 2),
            metas JSONB NOT NULL DEFAULT '{}',
            atualizado_em TIMESTAMP NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS preferencias CASCADE")
