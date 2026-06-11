"""usuarios_e_usuario_id

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-11

Introduz a tabela `usuarios` e o vinculo `transacoes.usuario_id` (FK CASCADE) em
3 fases na mesma migration, ordem fixa:

1. nullable: cria `usuarios` (email unico, telefone unico parcial, role default USER,
   ativo default true) e adiciona `usuario_id` NULL referenciando usuarios(id).
2. backfill: insere o usuario padrao (Jhonatas, ADMIN) com placeholder de senha que
   nao autentica, e aponta toda transacao orfa para esse usuario.
3. not null: torna `usuario_id` NOT NULL.

A migration nunca grava uma senha utilizavel. O hash placeholder nao verifica nenhuma
senha; a senha real e definida por scripts/criar_usuario.py (idempotente por email).
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            telefone TEXT,
            role TEXT NOT NULL DEFAULT 'USER',
            ativo BOOLEAN NOT NULL DEFAULT true,
            criado_em TIMESTAMP NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX ix_usuarios_telefone_unico "
        "ON usuarios (telefone) WHERE telefone IS NOT NULL"
    )
    op.execute(
        "ALTER TABLE transacoes "
        "ADD COLUMN usuario_id INTEGER NULL "
        "REFERENCES usuarios(id) ON DELETE CASCADE"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_transacoes_usuario_id "
        "ON transacoes(usuario_id)"
    )

    op.execute(
        "INSERT INTO usuarios (nome, username, email, senha_hash, role, ativo) "
        "VALUES ('Jhonatas','jhonatas','jhonatas2004@gmail.com',"
        "'!placeholder-sem-login!','ADMIN',true) "
        "ON CONFLICT (email) DO NOTHING"
    )
    op.execute(
        "UPDATE transacoes SET usuario_id = "
        "(SELECT id FROM usuarios WHERE email='jhonatas2004@gmail.com') "
        "WHERE usuario_id IS NULL"
    )

    op.execute("ALTER TABLE transacoes ALTER COLUMN usuario_id SET NOT NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_transacoes_usuario_id")
    op.execute("ALTER TABLE transacoes DROP COLUMN IF EXISTS usuario_id")
    op.execute("DROP TABLE IF EXISTS usuarios CASCADE")
