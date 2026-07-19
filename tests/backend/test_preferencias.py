import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test"
)

from contextlib import ExitStack
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session, get_session_begin
from backend.main import app

ALICE = UsuarioToken(usuario_id=1, role="USER", email="alice@exemplo.com")
BOB = UsuarioToken(usuario_id=2, role="USER", email="bob@exemplo.com")


def _override_session():
    async def _fake():
        yield SimpleNamespace()

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_session_begin] = _fake


def _override_usuario(usuario):
    async def _fake():
        return usuario

    app.dependency_overrides[get_usuario_atual] = _fake


def make_preferencias(usuario_id=1, renda="5000.00", metas=None):
    return SimpleNamespace(
        usuario_id=usuario_id,
        renda_mensal=Decimal(renda) if renda is not None else None,
        metas=metas if metas is not None else {},
        atualizado_em=datetime(2026, 7, 18, 12, 0, 0),
    )


def make_transacao(tipo, categoria, valor):
    return SimpleNamespace(
        tipo=tipo,
        categoria=categoria,
        valor=Decimal(valor),
        data=date(2026, 7, 1),
    )


def cliente_com(prefs_repo, transacao_repo=None, usuario=ALICE):
    _override_session()
    _override_usuario(usuario)
    stack = ExitStack()
    stack.enter_context(
        patch(
            "backend.services.preferencias.PreferenciasRepository",
            lambda session: prefs_repo,
        )
    )
    if transacao_repo is not None:
        stack.enter_context(
            patch(
                "backend.services.preferencias.TransacaoRepository",
                lambda session: transacao_repo,
            )
        )
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


# ---------------------------------------------------------------------------
# GET /api/preferencias
# ---------------------------------------------------------------------------

def test_get_sem_preferencias_retorna_objeto_vazio():
    repo = SimpleNamespace(obter=AsyncMock(return_value=None))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/preferencias")

    assert resposta.status_code == 200
    assert resposta.json() == {}
    assert repo.obter.await_args.args[0] == 1


def test_get_com_preferencias_retorna_dados():
    prefs = make_preferencias(metas={"ALIMENTACAO": 20, "INVESTIMENTO": 30})
    repo = SimpleNamespace(obter=AsyncMock(return_value=prefs))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/preferencias")

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["renda_mensal"] == "5000.00"
    assert corpo["metas"] == {"ALIMENTACAO": 20.0, "INVESTIMENTO": 30.0}


# ---------------------------------------------------------------------------
# PUT /api/preferencias — upsert e validação
# ---------------------------------------------------------------------------

def test_put_upsert_persiste_e_retorna():
    salvo = make_preferencias(renda="4000.00", metas={"ALIMENTACAO": 25.0})
    repo = SimpleNamespace(upsert=AsyncMock(return_value=salvo))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put(
            "/api/preferencias",
            json={"renda_mensal": "4000.00", "metas": {"ALIMENTACAO": 25}},
        )

    assert resposta.status_code == 200
    repo.upsert.assert_awaited_once()
    args = repo.upsert.await_args.args
    assert args[0] == 1
    assert args[1] == Decimal("4000.00")
    assert args[2] == {"ALIMENTACAO": 25.0}
    assert resposta.json()["metas"] == {"ALIMENTACAO": 25.0}


def test_put_soma_acima_de_100_retorna_400():
    repo = SimpleNamespace(upsert=AsyncMock())
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put(
            "/api/preferencias",
            json={"metas": {"ALIMENTACAO": 60, "INVESTIMENTO": 50}},
        )

    assert resposta.status_code == 400
    assert "erro" in resposta.json()
    repo.upsert.assert_not_awaited()


def test_put_soma_igual_100_aceita():
    salvo = make_preferencias(metas={"ALIMENTACAO": 60.0, "INVESTIMENTO": 40.0})
    repo = SimpleNamespace(upsert=AsyncMock(return_value=salvo))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put(
            "/api/preferencias",
            json={"metas": {"ALIMENTACAO": 60, "INVESTIMENTO": 40}},
        )

    assert resposta.status_code == 200


def test_put_categoria_invalida_retorna_400():
    repo = SimpleNamespace(upsert=AsyncMock())
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put(
            "/api/preferencias",
            json={"metas": {"CRIPTO": 10}},
        )

    assert resposta.status_code == 400
    repo.upsert.assert_not_awaited()


def test_put_percentual_fora_do_intervalo_retorna_400():
    repo = SimpleNamespace(upsert=AsyncMock())
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put(
            "/api/preferencias",
            json={"metas": {"ALIMENTACAO": 150}},
        )

    assert resposta.status_code == 400
    repo.upsert.assert_not_awaited()


# ---------------------------------------------------------------------------
# GET /api/preferencias/aderencia
# ---------------------------------------------------------------------------

def test_aderencia_com_saidas_calcula_percentuais():
    prefs = make_preferencias(metas={"ALIMENTACAO": 20, "INVESTIMENTO": 30})
    prefs_repo = SimpleNamespace(obter=AsyncMock(return_value=prefs))
    transacoes = [
        make_transacao("GASTO", "ALIMENTACAO", "300.00"),
        make_transacao("GASTO", "TRANSPORTE", "100.00"),
        make_transacao("INVESTIMENTO", "INVESTIMENTO", "600.00"),
        make_transacao("RECEITA", "RECEITA", "9999.00"),
    ]
    transacao_repo = SimpleNamespace(
        listar_por_periodo=AsyncMock(return_value=transacoes)
    )
    client, stack = cliente_com(prefs_repo, transacao_repo)
    with stack:
        resposta = client.get("/api/preferencias/aderencia?periodo=mes_atual")

    assert resposta.status_code == 200
    itens = {item["categoria"]: item for item in resposta.json()}
    # total_saidas = 300 + 100 + 600 = 1000 (receita ignorada)
    assert itens["ALIMENTACAO"]["realizado_valor"] == "300.00"
    assert itens["ALIMENTACAO"]["realizado_pct"] == 30.0
    assert itens["ALIMENTACAO"]["meta_pct"] == 20.0
    assert itens["ALIMENTACAO"]["desvio_pct"] == 10.0
    assert itens["INVESTIMENTO"]["realizado_valor"] == "600.00"
    assert itens["INVESTIMENTO"]["realizado_pct"] == 60.0
    assert itens["INVESTIMENTO"]["desvio_pct"] == 30.0
    assert transacao_repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 1


def test_aderencia_sem_saidas_nao_divide_por_zero():
    prefs = make_preferencias(metas={"ALIMENTACAO": 20})
    prefs_repo = SimpleNamespace(obter=AsyncMock(return_value=prefs))
    transacao_repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(prefs_repo, transacao_repo)
    with stack:
        resposta = client.get("/api/preferencias/aderencia")

    assert resposta.status_code == 200
    itens = resposta.json()
    assert len(itens) == 1
    assert itens[0]["realizado_valor"] == "0.00"
    assert itens[0]["realizado_pct"] == 0.0
    assert itens[0]["desvio_pct"] == -20.0


def test_aderencia_sem_preferencias_retorna_vazio():
    prefs_repo = SimpleNamespace(obter=AsyncMock(return_value=None))
    transacao_repo = SimpleNamespace(listar_por_periodo=AsyncMock())
    client, stack = cliente_com(prefs_repo, transacao_repo)
    with stack:
        resposta = client.get("/api/preferencias/aderencia")

    assert resposta.status_code == 200
    assert resposta.json() == []
    transacao_repo.listar_por_periodo.assert_not_awaited()


def test_aderencia_metas_vazias_retorna_vazio():
    prefs = make_preferencias(metas={})
    prefs_repo = SimpleNamespace(obter=AsyncMock(return_value=prefs))
    transacao_repo = SimpleNamespace(listar_por_periodo=AsyncMock())
    client, stack = cliente_com(prefs_repo, transacao_repo)
    with stack:
        resposta = client.get("/api/preferencias/aderencia")

    assert resposta.status_code == 200
    assert resposta.json() == []


# ---------------------------------------------------------------------------
# Isolamento por usuario
# ---------------------------------------------------------------------------

def test_get_isola_por_usuario():
    repo = SimpleNamespace(obter=AsyncMock(return_value=None))
    client, stack = cliente_com(repo, usuario=BOB)
    with stack:
        client.get("/api/preferencias")

    assert repo.obter.await_args.args[0] == 2


def test_put_isola_por_usuario():
    salvo = make_preferencias(usuario_id=2, metas={"LAZER": 10.0})
    repo = SimpleNamespace(upsert=AsyncMock(return_value=salvo))
    client, stack = cliente_com(repo, usuario=BOB)
    with stack:
        client.put("/api/preferencias", json={"metas": {"LAZER": 10}})

    assert repo.upsert.await_args.args[0] == 2


def test_aderencia_isola_por_usuario():
    prefs = make_preferencias(usuario_id=2, metas={"ALIMENTACAO": 10})
    prefs_repo = SimpleNamespace(obter=AsyncMock(return_value=prefs))
    transacao_repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(prefs_repo, transacao_repo, usuario=BOB)
    with stack:
        client.get("/api/preferencias/aderencia")

    assert prefs_repo.obter.await_args.args[0] == 2
    assert transacao_repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 2
