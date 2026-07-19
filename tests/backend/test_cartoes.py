import os

for var, valor in {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test",
}.items():
    os.environ.setdefault(var, valor)

from contextlib import ExitStack
from datetime import date, timedelta
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

    async def _fake_usuario():
        return ALICE

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_session_begin] = _fake
    app.dependency_overrides[get_usuario_atual] = _fake_usuario


def cliente(patches: dict):
    _override_session()
    stack = ExitStack()
    for caminho, repo in patches.items():
        stack.enter_context(patch(caminho, lambda session, _r=repo: _r))
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


def make_cartao(id=1, apelido="Nubank", dia_fechamento=10, dia_vencimento=17,
                cor="#820ad1", ativo=True):
    return SimpleNamespace(
        id=id,
        apelido=apelido,
        dia_fechamento=dia_fechamento,
        dia_vencimento=dia_vencimento,
        cor=cor,
        ativo=ativo,
    )


def make_transacao(id, valor="10.00", data=None, parcela_total=1,
                   status="PENDENTE", cartao_id=None, grupo=None):
    return SimpleNamespace(
        id=id,
        data=data or date.today(),
        descricao=f"desc-{id}",
        categoria="COMPRAS",
        valor=Decimal(valor),
        parcela_numero=1,
        parcela_total=parcela_total,
        tipo="GASTO",
        grupo_parcela_id=grupo or f"grupo-{id}",
        status=status,
        forma_pagamento="CARTAO_CREDITO",
        recorrente=False,
        responsavel="Jhonatas",
        detalhes=None,
        cartao_id=cartao_id,
    )


def fake_cartao_repo(**overrides):
    repo = SimpleNamespace(
        listar=AsyncMock(return_value=[]),
        buscar_por_id=AsyncMock(return_value=None),
        criar=AsyncMock(side_effect=lambda c: c),
        atualizar=AsyncMock(side_effect=lambda c: c),
        excluir=AsyncMock(return_value=None),
    )
    for nome, valor in overrides.items():
        setattr(repo, nome, valor)
    return repo


def fake_transacao_repo(**overrides):
    repo = SimpleNamespace(
        listar_por_periodo=AsyncMock(return_value=[]),
        listar_por_cartao=AsyncMock(return_value=[]),
        listar_por_ids=AsyncMock(return_value=[]),
        vincular_cartao=AsyncMock(return_value=0),
    )
    for nome, valor in overrides.items():
        setattr(repo, nome, valor)
    return repo


CARTAO_REPO = "backend.services.cartoes.CartaoRepository"
CARTAO_TRANSACAO_REPO = "backend.services.cartoes.TransacaoRepository"
TRANSACAO_REPO = "backend.services.transacoes.TransacaoRepository"
TRANSACAO_CARTAO_REPO = "backend.services.transacoes.CartaoRepository"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def test_listar_cartoes():
    repo = fake_cartao_repo(
        listar=AsyncMock(return_value=[make_cartao(1), make_cartao(2, apelido="Itau")])
    )
    client, stack = cliente({CARTAO_REPO: repo})
    with stack:
        resposta = client.get("/api/cartoes")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 2
    assert corpo[0] == {
        "id": 1, "apelido": "Nubank", "dia_fechamento": 10,
        "dia_vencimento": 17, "cor": "#820ad1", "ativo": True,
    }
    assert repo.listar.await_args.args[0] == 1


def test_criar_cartao():
    criado = make_cartao(7, apelido="Inter", cor="#ff7a00")
    repo = fake_cartao_repo(criar=AsyncMock(return_value=criado))
    client, stack = cliente({CARTAO_REPO: repo})
    with stack:
        resposta = client.post(
            "/api/cartoes",
            json={"apelido": "Inter", "dia_fechamento": 5, "dia_vencimento": 12, "cor": "#ff7a00"},
        )

    assert resposta.status_code == 201
    assert resposta.json()["id"] == 7
    cartao = repo.criar.await_args.args[0]
    assert cartao.usuario_id == 1
    assert cartao.apelido == "Inter"
    assert cartao.dia_fechamento == 5


def test_criar_cartao_sem_apelido_retorna_400():
    repo = fake_cartao_repo()
    client, stack = cliente({CARTAO_REPO: repo})
    with stack:
        resposta = client.post("/api/cartoes", json={"cor": "#000000"})

    assert resposta.status_code == 400
    repo.criar.assert_not_awaited()


def test_criar_cartao_dia_invalido_retorna_400():
    repo = fake_cartao_repo()
    client, stack = cliente({CARTAO_REPO: repo})
    with stack:
        resposta = client.post(
            "/api/cartoes", json={"apelido": "X", "dia_fechamento": 40}
        )

    assert resposta.status_code == 400
    repo.criar.assert_not_awaited()


def test_atualizar_cartao():
    existente = make_cartao(3, apelido="Antigo", ativo=True)
    repo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente({CARTAO_REPO: repo})
    with stack:
        resposta = client.put("/api/cartoes/3", json={"apelido": "Novo", "ativo": False})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["apelido"] == "Novo"
    assert corpo["ativo"] is False
    repo.buscar_por_id.assert_awaited_once_with(3, 1)


def test_excluir_cartao():
    repo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=make_cartao(4)))
    client, stack = cliente({CARTAO_REPO: repo})
    with stack:
        resposta = client.delete("/api/cartoes/4")

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    repo.excluir.assert_awaited_once_with(4, 1)


# ---------------------------------------------------------------------------
# Isolamento — cartão de outro usuário → 404
# ---------------------------------------------------------------------------

def test_atualizar_cartao_de_outro_usuario_retorna_404():
    repo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente({CARTAO_REPO: repo})
    with stack:
        resposta = client.put("/api/cartoes/99", json={"apelido": "Hack"})

    assert resposta.status_code == 404
    repo.atualizar.assert_not_awaited()


def test_excluir_cartao_de_outro_usuario_retorna_404():
    repo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente({CARTAO_REPO: repo})
    with stack:
        resposta = client.delete("/api/cartoes/99")

    assert resposta.status_code == 404
    repo.excluir.assert_not_awaited()


def test_resumo_cartao_de_outro_usuario_retorna_404():
    repo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=None))
    trepo = fake_transacao_repo()
    client, stack = cliente({CARTAO_REPO: repo, CARTAO_TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.get("/api/cartoes/99/resumo")

    assert resposta.status_code == 404
    trepo.listar_por_cartao.assert_not_awaited()


# ---------------------------------------------------------------------------
# Delete não apaga transações — apenas o cartão é excluído (SET NULL no banco)
# ---------------------------------------------------------------------------

def test_excluir_cartao_nao_toca_transacoes():
    repo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=make_cartao(4)))
    trepo = fake_transacao_repo()
    client, stack = cliente({CARTAO_REPO: repo, CARTAO_TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.delete("/api/cartoes/4")

    assert resposta.status_code == 200
    trepo.vincular_cartao.assert_not_awaited()
    repo.excluir.assert_awaited_once_with(4, 1)


# ---------------------------------------------------------------------------
# Resumo do cartão
# ---------------------------------------------------------------------------

def test_resumo_cartao():
    ano_passado = date.today() - timedelta(days=365)
    transacoes = [
        make_transacao(1, valor="100.00", parcela_total=1, status="PAGO"),
        make_transacao(2, valor="50.00", parcela_total=3, status="PENDENTE"),
        make_transacao(3, valor="50.00", data=ano_passado, parcela_total=3, status="PENDENTE"),
    ]
    repo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=make_cartao(5)))
    trepo = fake_transacao_repo(listar_por_cartao=AsyncMock(return_value=transacoes))
    client, stack = cliente({CARTAO_REPO: repo, CARTAO_TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.get("/api/cartoes/5/resumo?periodo=mes_atual")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total_periodo"] == "150.00"
    assert corpo["parcelas_abertas"] == 2
    assert corpo["soma_restante"] == "100.00"
    assert trepo.listar_por_cartao.await_args.args == (5, 1)


# ---------------------------------------------------------------------------
# Filtros cartao_id / sem_cartao em GET /api/transacoes
# ---------------------------------------------------------------------------

def test_filtro_cartao_id():
    transacoes = [
        make_transacao(1, cartao_id=5),
        make_transacao(2, cartao_id=9),
        make_transacao(3, cartao_id=None),
        make_transacao(4, cartao_id=5),
    ]
    repo = fake_transacao_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente({TRANSACAO_REPO: repo})
    with stack:
        resposta = client.get("/api/transacoes?cartao_id=5&periodo=tudo")

    corpo = resposta.json()
    assert corpo["total"] == 2
    assert {item["id"] for item in corpo["itens"]} == {1, 4}


def test_filtro_sem_cartao():
    transacoes = [
        make_transacao(1, cartao_id=5),
        make_transacao(2, cartao_id=None),
        make_transacao(3, cartao_id=None),
    ]
    repo = fake_transacao_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente({TRANSACAO_REPO: repo})
    with stack:
        resposta = client.get("/api/transacoes?sem_cartao=true&periodo=tudo")

    corpo = resposta.json()
    assert corpo["total"] == 2
    assert {item["id"] for item in corpo["itens"]} == {2, 3}


# ---------------------------------------------------------------------------
# PATCH /api/transacoes/cartao — vínculo em lote + propagação no grupo
# ---------------------------------------------------------------------------

def test_vincular_cartao_em_lote():
    transacoes = [
        make_transacao(10, parcela_total=1),
        make_transacao(20, parcela_total=3, grupo="grupo-parcelado"),
    ]
    crepo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=make_cartao(5)))
    trepo = fake_transacao_repo(
        listar_por_ids=AsyncMock(return_value=transacoes),
        vincular_cartao=AsyncMock(return_value=4),
    )
    client, stack = cliente({TRANSACAO_CARTAO_REPO: crepo, TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.patch(
            "/api/transacoes/cartao", json={"ids": [10, 20], "cartao_id": 5}
        )

    assert resposta.status_code == 200
    assert resposta.json() == {"atualizados": 4}
    ids_diretos, grupos, cartao_id, usuario_id = trepo.vincular_cartao.await_args.args
    assert ids_diretos == [10]
    assert grupos == ["grupo-parcelado"]
    assert cartao_id == 5
    assert usuario_id == 1


def test_vincular_cartao_null_desvincula():
    transacoes = [make_transacao(10, parcela_total=1)]
    crepo = fake_cartao_repo()
    trepo = fake_transacao_repo(
        listar_por_ids=AsyncMock(return_value=transacoes),
        vincular_cartao=AsyncMock(return_value=1),
    )
    client, stack = cliente({TRANSACAO_CARTAO_REPO: crepo, TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.patch(
            "/api/transacoes/cartao", json={"ids": [10], "cartao_id": None}
        )

    assert resposta.status_code == 200
    assert resposta.json() == {"atualizados": 1}
    crepo.buscar_por_id.assert_not_awaited()
    assert trepo.vincular_cartao.await_args.args[2] is None


def test_vincular_cartao_ids_vazio_retorna_400():
    crepo = fake_cartao_repo()
    trepo = fake_transacao_repo()
    client, stack = cliente({TRANSACAO_CARTAO_REPO: crepo, TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.patch(
            "/api/transacoes/cartao", json={"ids": [], "cartao_id": 5}
        )

    assert resposta.status_code == 400
    trepo.vincular_cartao.assert_not_awaited()


def test_vincular_cartao_de_outro_usuario_retorna_404():
    crepo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=None))
    trepo = fake_transacao_repo()
    client, stack = cliente({TRANSACAO_CARTAO_REPO: crepo, TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.patch(
            "/api/transacoes/cartao", json={"ids": [10], "cartao_id": 99}
        )

    assert resposta.status_code == 404
    trepo.vincular_cartao.assert_not_awaited()


# ---------------------------------------------------------------------------
# POST /api/transacoes com cartao_id
# ---------------------------------------------------------------------------

def test_post_transacao_com_cartao_valido():
    crepo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=make_cartao(5)))
    trepo = fake_transacao_repo()
    trepo.criar = AsyncMock(return_value=SimpleNamespace(id=77))
    client, stack = cliente({TRANSACAO_CARTAO_REPO: crepo, TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
                "cartao_id": 5,
            },
        )

    assert resposta.status_code == 201
    assert trepo.criar.await_args.args[0].cartao_id == 5


def test_post_transacao_com_cartao_invalido_retorna_400():
    crepo = fake_cartao_repo(buscar_por_id=AsyncMock(return_value=None))
    trepo = fake_transacao_repo()
    trepo.criar = AsyncMock(return_value=SimpleNamespace(id=77))
    client, stack = cliente({TRANSACAO_CARTAO_REPO: crepo, TRANSACAO_REPO: trepo})
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
                "cartao_id": 99,
            },
        )

    assert resposta.status_code == 400
    trepo.criar.assert_not_awaited()
