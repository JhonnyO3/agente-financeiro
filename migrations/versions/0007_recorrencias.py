"""recorrencias

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-18

Introduz o modelo de recorrencias (Modelo A - materializacao):

1. tabela `recorrencias`: fonte da verdade das assinaturas/gastos fixos por usuario.
2. tabela `recorrencia_lancamentos`: log de idempotencia (uma linha por
   recorrencia+competencia) que impede recriar uma transacao materializada mesmo
   depois de a transacao ter sido apagada.
3. coluna `transacoes.recorrencia_id`: vinculo (FK SET NULL) da transacao
   materializada com a recorrencia que a originou.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE recorrencias (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            descricao VARCHAR NOT NULL,
            tipo VARCHAR NOT NULL,
            categoria VARCHAR NOT NULL,
            valor DECIMAL(12, 2) NOT NULL,
            dia_vencimento INTEGER,
            forma_pagamento VARCHAR,
            ativo BOOLEAN NOT NULL DEFAULT true,
            criado_em TIMESTAMP DEFAULT now(),
            encerrado_em TIMESTAMP
        )
    """)
    op.execute(
        "CREATE INDEX ix_recorrencias_usuario_ativo "
        "ON recorrencias (usuario_id, ativo)"
    )

    op.execute("""
        CREATE TABLE recorrencia_lancamentos (
            id SERIAL PRIMARY KEY,
            recorrencia_id INTEGER NOT NULL
                REFERENCES recorrencias(id) ON DELETE CASCADE,
            competencia DATE NOT NULL,
            transacao_id INTEGER REFERENCES transacoes(id) ON DELETE SET NULL,
            gerado_em TIMESTAMP DEFAULT now(),
            UNIQUE (recorrencia_id, competencia)
        )
    """)

    op.execute(
        "ALTER TABLE transacoes "
        "ADD COLUMN recorrencia_id INTEGER NULL "
        "REFERENCES recorrencias(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX ix_transacoes_recorrencia_id "
        "ON transacoes (recorrencia_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_transacoes_recorrencia_id")
    op.execute("ALTER TABLE transacoes DROP COLUMN IF EXISTS recorrencia_id")
    op.execute("DROP TABLE IF EXISTS recorrencia_lancamentos")
    op.execute("DROP INDEX IF EXISTS ix_recorrencias_usuario_ativo")
    op.execute("DROP TABLE IF EXISTS recorrencias")
