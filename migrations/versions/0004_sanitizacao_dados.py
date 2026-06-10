"""sanitizacao_dados

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-10

Migração de dados (RF-08): sanitiza os registros legados de `transacoes` para o
estado corrigido manualmente pelo usuário (`dados-corrigidos.txt`).

Aplica, via `op.execute`, de forma idempotente:
  1. `CARTAO` -> `CARTAO_CREDITO`; `OUTRO` remanescente resolvido por parcela/recorrência
     (parcelado ou recorrente -> `CARTAO_CREDITO`; à vista -> `PIX`). Nenhum `OUTRO` sobra.
  2. Recategorização por descrição (EDUCACAO/COMPRAS/GASTOS_PONTUAIS) e ajuste de `tipo`.
  3. Recorrentes (academia, LinkedIn, Spotify) -> recorrente=TRUE, parcela 1/1.
  4. Valores corrigidos (aquecedor, carro, Nubank, cuecas, batman, celular).
  5. Remoção de itens de teste (Coxinha, Sorvete do Mac, tokens open ai, Claude code 472).
  6. Inserção de recorrentes (Google Drive, Claude code Max) — condicional por descrição.
  7. `zara` recebe `grupo_parcela_id` próprio, desvinculado do grupo do batman.

Idempotência: cada statement carrega guardas (`WHERE` por valor-alvo, `CASE`
determinístico, `INSERT ... WHERE NOT EXISTS`). Reaplicar `upgrade` não duplica nem
corrompe os dados.

ATENÇÃO — `downgrade` é IRREVERSÍVEL EM DADOS. Os valores, categorias, formas e
registros originais não são restaurados (a base original não é preservada). O
`downgrade` apenas registra essa impossibilidade e não altera dados; o rollback de
schema é responsabilidade da 0003.
"""
from typing import Sequence, Union

from alembic import op

from scripts.sanitizacao import sql_sanitizacao


revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for statement in sql_sanitizacao():
        op.execute(statement)


def downgrade() -> None:
    op.execute(
        "SELECT 'migration 0004 (sanitizacao de dados) e irreversivel em dados; "
        "nenhuma restauracao foi aplicada'"
    )
