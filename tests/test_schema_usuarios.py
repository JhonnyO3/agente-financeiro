"""Testes do schema de usuarios e do vinculo usuario_id em transacoes (T02).

Sem Postgres real: inspeciona metadata do ORM e o texto-fonte da migration.
Baseado em scenarios/02-schema-usuarios.feature.
"""

import re
from pathlib import Path

import pytest

PROJETO = Path(__file__).resolve().parent.parent
MIGRATION = PROJETO / "migrations" / "versions" / "0006_usuarios_e_usuario_id.py"


# ---------------------------------------------------------------------------
# RoleEnum
# ---------------------------------------------------------------------------


def test_role_enum_tem_admin_e_user():
    from backend.models.enums import RoleEnum

    assert RoleEnum.ADMIN.value == "ADMIN"
    assert RoleEnum.USER.value == "USER"
    assert {m.value for m in RoleEnum} == {"ADMIN", "USER"}


def test_role_enum_e_str():
    from backend.models.enums import RoleEnum

    assert issubclass(RoleEnum, str)


def test_role_enum_rejeita_valor_invalido():
    from backend.models.enums import RoleEnum

    with pytest.raises(ValueError):
        RoleEnum("SUPERUSER")


# ---------------------------------------------------------------------------
# ORM Usuario
# ---------------------------------------------------------------------------


def test_usuario_mapeado_em_usuarios():
    from backend.models.usuario import Usuario

    assert Usuario.__tablename__ == "usuarios"


def test_usuario_usa_mesma_base_da_transacao():
    from backend.models.transacao import Base
    from backend.models.usuario import Usuario

    assert Usuario.__table__.metadata is Base.metadata


def test_usuario_tem_colunas_esperadas():
    from backend.models.usuario import Usuario

    colunas = set(Usuario.__table__.columns.keys())
    assert {
        "id",
        "nome",
        "username",
        "email",
        "senha_hash",
        "telefone",
        "role",
        "ativo",
        "criado_em",
    } <= colunas


def test_usuario_nao_tem_coluna_senha_em_texto_puro():
    from backend.models.usuario import Usuario

    colunas = set(Usuario.__table__.columns.keys())
    assert "senha" not in colunas
    assert "password" not in colunas
    assert "senha_hash" in colunas


def test_usuario_id_pk_autoincrement():
    from backend.models.usuario import Usuario

    coluna = Usuario.__table__.columns["id"]
    assert coluna.primary_key is True
    assert coluna.autoincrement is True


def test_usuario_email_not_null_e_unique():
    from backend.models.usuario import Usuario

    coluna = Usuario.__table__.columns["email"]
    assert coluna.nullable is False
    assert coluna.unique is True


def test_usuario_nome_username_senha_hash_not_null():
    from backend.models.usuario import Usuario

    for nome in ("nome", "username", "senha_hash"):
        assert Usuario.__table__.columns[nome].nullable is False


def test_usuario_telefone_nullable_com_indice_unico_parcial():
    from backend.models.usuario import Usuario

    assert Usuario.__table__.columns["telefone"].nullable is True

    indices_parciais = [
        idx
        for idx in Usuario.__table__.indexes
        if idx.unique
        and "telefone" in {c.name for c in idx.columns}
        and idx.dialect_options["postgresql"]["where"] is not None
    ]
    assert len(indices_parciais) == 1


def test_usuario_role_default_user():
    from backend.models.enums import RoleEnum
    from backend.models.usuario import Usuario

    coluna = Usuario.__table__.columns["role"]
    assert coluna.nullable is False
    assert coluna.server_default is not None
    assert "USER" in str(coluna.server_default.arg)
    assert RoleEnum.USER.value == "USER"


def test_usuario_ativo_default_true():
    from backend.models.usuario import Usuario

    coluna = Usuario.__table__.columns["ativo"]
    assert coluna.nullable is False
    assert coluna.server_default is not None


def test_usuario_criado_em_server_default_now():
    from backend.models.usuario import Usuario

    coluna = Usuario.__table__.columns["criado_em"]
    assert coluna.nullable is False
    assert coluna.server_default is not None


# ---------------------------------------------------------------------------
# Transacao.usuario_id
# ---------------------------------------------------------------------------


def test_transacao_tem_usuario_id_not_null():
    from backend.models.transacao import Transacao

    coluna = Transacao.__table__.columns["usuario_id"]
    assert coluna.nullable is False


def test_transacao_usuario_id_fk_cascade():
    from backend.models.transacao import Transacao

    coluna = Transacao.__table__.columns["usuario_id"]
    fks = list(coluna.foreign_keys)
    assert len(fks) == 1
    fk = fks[0]
    assert fk.column.table.name == "usuarios"
    assert fk.column.name == "id"
    assert fk.ondelete == "CASCADE"


# ---------------------------------------------------------------------------
# Migration 0006 — texto-fonte
# ---------------------------------------------------------------------------


def test_migration_existe():
    assert MIGRATION.is_file()


def test_migration_tem_upgrade_e_downgrade():
    from importlib import import_module

    modulo = import_module("migrations.versions.0006_usuarios_e_usuario_id")
    assert callable(modulo.upgrade)
    assert callable(modulo.downgrade)


def test_migration_revisao_e_down_revision():
    from importlib import import_module

    modulo = import_module("migrations.versions.0006_usuarios_e_usuario_id")
    assert modulo.revision == "0006"
    assert modulo.down_revision == "0005"


def test_migration_cria_usuarios_e_coluna_usuario_id():
    texto = MIGRATION.read_text(encoding="utf-8").upper()
    assert "CREATE TABLE USUARIOS" in texto
    assert "ADD COLUMN USUARIO_ID" in texto
    assert "ON DELETE CASCADE" in texto


def test_migration_email_unique_e_telefone_unico_parcial():
    texto = MIGRATION.read_text(encoding="utf-8")
    texto_upper = texto.upper()
    assert "UNIQUE" in texto_upper and "EMAIL" in texto_upper
    assert "WHERE TELEFONE IS NOT NULL" in texto_upper


def test_migration_ordem_nullable_backfill_notnull():
    texto = MIGRATION.read_text(encoding="utf-8").upper()

    pos_create = texto.find("CREATE TABLE USUARIOS")
    pos_add_col = texto.find("ADD COLUMN USUARIO_ID")
    pos_insert = texto.find("INSERT INTO USUARIOS")
    pos_update = texto.find("UPDATE TRANSACOES SET USUARIO_ID")
    pos_set_not_null = texto.find("SET NOT NULL")

    for pos in (pos_create, pos_add_col, pos_insert, pos_update, pos_set_not_null):
        assert pos != -1

    assert pos_create < pos_add_col < pos_insert < pos_update < pos_set_not_null


def test_migration_backfill_insere_jhonatas_admin():
    texto = MIGRATION.read_text(encoding="utf-8")
    assert "jhonatas2004@gmail.com" in texto
    assert "ON CONFLICT" in texto.upper()
    assert "DO NOTHING" in texto.upper()
    assert "ADMIN" in texto


def test_migration_nao_grava_senha_real_apenas_placeholder():
    texto = MIGRATION.read_text(encoding="utf-8")
    assert "!placeholder-sem-login!" in texto

    hashes_bcrypt = re.findall(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}", texto)
    assert hashes_bcrypt == []


def test_migration_downgrade_reverte():
    texto = MIGRATION.read_text(encoding="utf-8").upper()
    assert "DROP COLUMN USUARIO_ID" in texto or "DROP COLUMN IF EXISTS USUARIO_ID" in texto
    assert "DROP TABLE" in texto and "USUARIOS" in texto
