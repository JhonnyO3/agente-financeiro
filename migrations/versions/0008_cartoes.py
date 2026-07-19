"""cartoes

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-18

Introduz a tabela `cartoes` (isolada por usuario_id, FK CASCADE) e o vinculo
`transacoes.cartao_id` (FK cartoes(id) ON DELETE SET NULL). O SET NULL garante que
excluir um cartao nao apaga as transacoes vinculadas: apenas as desvincula.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS cartoes (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            apelido VARCHAR NOT NULL,
            dia_fechamento INTEGER,
            dia_vencimento INTEGER,
            cor VARCHAR,
            ativo BOOLEAN NOT NULL DEFAULT true,
            criado_em TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_cartoes_usuario_id ON cartoes(usuario_id)"
    )
    op.execute(
        "ALTER TABLE transacoes "
        "ADD COLUMN IF NOT EXISTS cartao_id INTEGER NULL "
        "REFERENCES cartoes(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_transacoes_cartao_id "
        "ON transacoes(cartao_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_transacoes_cartao_id")
    op.execute("ALTER TABLE transacoes DROP COLUMN IF EXISTS cartao_id")
    op.execute("DROP INDEX IF EXISTS ix_cartoes_usuario_id")
    op.execute("DROP TABLE IF EXISTS cartoes CASCADE")
