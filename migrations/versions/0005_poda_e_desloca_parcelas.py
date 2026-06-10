"""poda_e_desloca_parcelas

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-10

Correcoes de data que faltaram na 0004 (sanitizacao manual da base):

- R-B: desloca +1 mes as parcelas (parcela_total > 1) no cartao de credito — a parcela
  cai na fatura do mes seguinte. A fatura do Nubank fica de fora (usa a data real).
- R-A: remove as parcelas que, apos o deslocamento, ficaram com vencimento anterior ao
  mes corrente (2026-06).
- Recalcula o status das parcelas pela nova data (<= 2026-06-10 = PAGO; futura = PENDENTE).

Migracao de dados pontual, ancorada em 2026-06. Nao e idempotente (o Alembic garante
execucao unica). O downgrade nao restaura linhas removidas nem datas originais.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE transacoes "
        "SET data = (data + INTERVAL '1 month')::date "
        "WHERE parcela_total > 1 "
        "AND forma_pagamento = 'CARTAO_CREDITO' "
        "AND descricao <> 'Nubank' "
        "AND data IS NOT NULL"
    )
    op.execute(
        "DELETE FROM transacoes "
        "WHERE parcela_total > 1 AND data < DATE '2026-06-01'"
    )
    op.execute(
        "UPDATE transacoes "
        "SET status = CASE WHEN data <= DATE '2026-06-10' THEN 'PAGO' ELSE 'PENDENTE' END "
        "WHERE parcela_total > 1 AND data IS NOT NULL"
    )


def downgrade() -> None:
    pass
