import os

for var, valor in {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test",
}.items():
    os.environ.setdefault(var, valor)

from contextlib import ExitStack
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session, get_session_begin
from backend.main import app

ALICE = UsuarioToken(usuario_id=1, role="USER", email="alice@exemplo.com")
BOB = UsuarioToken(usuario_id=2, role="USER", email="bob@exemplo.com")

CAMINHOS_REPO = (
    "backend.services.transacoes.TransacaoRepository",
    "backend.services.resumo.TransacaoRepository",
    "backend.services.parcelas.TransacaoRepository",
    "backend.controllers.graficos.TransacaoRepository",
    "backend.controllers.projecao.TransacaoRepository",
)


def _override_session():
    async def _fake():
        yield SimpleNamespace()

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_session_begin] = _fake


def _override_usuario(usuario):
    async def _fake():
        return usuario

    app.dependency_overrides[get_usuario_atual] = _fake


def fake_repo(**overrides):
    repo = SimpleNamespace(
        listar_por_periodo=AsyncMock(return_value=[]),
        criar=AsyncMock(return_value=SimpleNamespace(id=43)),
        buscar_por_id=AsyncMock(return_value=None),
        atualizar=AsyncMock(return_value=None),
        excluir=AsyncMock(return_value=None),
        excluir_grupo=AsyncMock(return_value=0),
    )
    for nome, valor in overrides.items():
        setattr(repo, nome, valor)
    return repo


def cliente_com(repo, usuario=ALICE):
    _override_session()
    if usuario is not None:
        _override_usuario(usuario)
    stack = ExitStack()
    for caminho in CAMINHOS_REPO:
        stack.enter_context(patch(caminho, lambda session: repo))
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


def make_transacao(
    id,
    usuario_id=1,
    dia=1,
    tipo="GASTO",
    categoria="COMPRAS",
    valor="10.00",
    status="PENDENTE",
    forma_pagamento="PIX",
    parcela_numero=1,
    parcela_total=1,
    grupo_parcela_id=None,
):
    return SimpleNamespace(
        id=id,
        usuario_id=usuario_id,
        data=date(2026, 6, dia),
        descricao=f"desc-{id}",
        categoria=categoria,
        valor=Decimal(valor),
        parcela_numero=parcela_numero,
        parcela_total=parcela_total,
        tipo=tipo,
        grupo_parcela_id=grupo_parcela_id or f"grupo-{id}",
        status=status,
        forma_pagamento=forma_pagamento,
        responsavel="Jhonatas",
        detalhes=None,
    )


# ---------------------------------------------------------------------------
# Proteção — sem Bearer → 401
# ---------------------------------------------------------------------------

ENDPOINTS_GET_PROTEGIDOS = [
    "/api/transacoes",
    "/api/resumo?periodo=2026-06",
    "/api/grafico/categorias?periodo=2026-06",
    "/api/grafico/mensal",
    "/api/grafico/evolucao",
    "/api/parcelas-ativas",
    "/api/projecao",
]


def test_get_sem_bearer_retorna_401():
    _override_session()
    app.dependency_overrides.pop(get_usuario_atual, None)
    client = TestClient(app)
    try:
        for rota in ENDPOINTS_GET_PROTEGIDOS:
            resposta = client.get(rota)
            assert resposta.status_code == 401, rota
            assert resposta.json() == {"erro": "não autenticado"}, rota
    finally:
        app.dependency_overrides.clear()


def test_post_transacoes_sem_bearer_retorna_401():
    _override_session()
    app.dependency_overrides.pop(get_usuario_atual, None)
    client = TestClient(app)
    try:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )
        assert resposta.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_delete_grupo_sem_bearer_retorna_401():
    _override_session()
    app.dependency_overrides.pop(get_usuario_atual, None)
    client = TestClient(app)
    try:
        resposta = client.delete("/api/grupos/grupo-xyz")
        assert resposta.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_health_permanece_publico():
    app.dependency_overrides.clear()
    client = TestClient(app)
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Isolamento entre usuários — GET /api/transacoes
# ---------------------------------------------------------------------------

def test_alice_lista_apenas_proprias_transacoes():
    transacoes = [make_transacao(i, usuario_id=1, dia=i) for i in range(1, 4)]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.get("/api/transacoes")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["total"] == 3
    repo.listar_por_periodo.assert_awaited_once()
    assert repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 1


def test_bob_lista_apenas_proprias_transacoes():
    transacoes = [make_transacao(i, usuario_id=2, dia=i) for i in range(1, 3)]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo, usuario=BOB)
    with stack:
        resposta = client.get("/api/transacoes")

    assert resposta.status_code == 200
    assert resposta.json()["total"] == 2
    assert repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 2


def test_shape_json_transacoes_identico():
    t = make_transacao(42, usuario_id=1, dia=9, valor="100.00", categoria="ALIMENTACAO")
    t.descricao = "Coxinha"
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[t]))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.get("/api/transacoes")

    item = resposta.json()["itens"][0]
    assert item == {
        "id": 42,
        "data": "2026-06-09",
        "descricao": "Coxinha",
        "categoria": "ALIMENTACAO",
        "valor": "100.00",
        "parcela_numero": 1,
        "parcela_total": 1,
        "tipo": "GASTO",
        "grupo_parcela_id": "grupo-42",
        "status": "PENDENTE",
        "forma_pagamento": "PIX",
        "responsavel": "Jhonatas",
        "detalhes": "",
    }


# ---------------------------------------------------------------------------
# POST /api/transacoes — usuario_id do body é ignorado
# ---------------------------------------------------------------------------

def test_post_usa_usuario_id_do_token_ignora_body():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=99)))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
                "usuario_id": 2,
            },
        )

    assert resposta.status_code == 201
    dto = repo.criar.await_args.args[0]
    assert dto.usuario_id == 1


# ---------------------------------------------------------------------------
# PUT /api/transacoes/{id} — isolamento de dono
# ---------------------------------------------------------------------------

def test_put_propria_transacao_sucesso():
    existente = make_transacao(10, usuario_id=1)
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.put("/api/transacoes/10", json={"valor": "75.00"})

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    repo.buscar_por_id.assert_awaited_once_with(10, usuario_id=1)
    assert repo.atualizar.await_args.kwargs["usuario_id"] == 1


def test_put_transacao_de_outro_usuario_retorna_404():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.put("/api/transacoes/20", json={"valor": "75.00"})

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "Transacao nao encontrada"}
    repo.atualizar.assert_not_awaited()


# ---------------------------------------------------------------------------
# DELETE /api/transacoes/{id} — isolamento de dono
# ---------------------------------------------------------------------------

def test_delete_propria_transacao_sucesso():
    existente = make_transacao(11, usuario_id=1)
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.delete("/api/transacoes/11")

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    repo.buscar_por_id.assert_awaited_once_with(11, usuario_id=1)
    assert repo.excluir.await_args.kwargs["usuario_id"] == 1


def test_delete_transacao_de_outro_usuario_retorna_404():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.delete("/api/transacoes/21")

    assert resposta.status_code == 404
    repo.excluir.assert_not_awaited()


# ---------------------------------------------------------------------------
# DELETE /api/grupos/{grupo} — isolamento de dono
# ---------------------------------------------------------------------------

GRUPO_VALIDO = "11111111-1111-1111-1111-111111111111"


def test_delete_grupo_proprio_sucesso():
    repo = fake_repo(excluir_grupo=AsyncMock(return_value=3))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.delete(f"/api/grupos/{GRUPO_VALIDO}")

    assert resposta.status_code == 200
    assert resposta.json()["ok"] is True
    assert repo.excluir_grupo.await_args.kwargs["usuario_id"] == 1


def test_delete_grupo_de_outro_usuario_retorna_404():
    repo = fake_repo(excluir_grupo=AsyncMock(return_value=0))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.delete(f"/api/grupos/{GRUPO_VALIDO}")

    assert resposta.status_code == 404
    assert repo.excluir_grupo.await_args.kwargs["usuario_id"] == 1


# ---------------------------------------------------------------------------
# Isolamento em endpoints agregados
# ---------------------------------------------------------------------------

def test_resumo_filtra_por_usuario():
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.get("/api/resumo?periodo=mes_atual")

    assert resposta.status_code == 200
    assert repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 1


def test_categorias_filtra_por_usuario():
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.get("/api/grafico/categorias?periodo=mes_atual")

    assert resposta.status_code == 200
    assert repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 1


def test_parcelas_ativas_filtra_por_usuario():
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.get("/api/parcelas-ativas")

    assert resposta.status_code == 200
    assert repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 1


def test_grafico_mensal_filtra_por_usuario():
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.get("/api/grafico/mensal")

    assert resposta.status_code == 200
    assert repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 1


def test_grafico_evolucao_filtra_por_usuario():
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.get("/api/grafico/evolucao")

    assert resposta.status_code == 200
    assert repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 1


def test_projecao_filtra_por_usuario():
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(repo, usuario=ALICE)
    with stack:
        resposta = client.get("/api/projecao")

    assert resposta.status_code == 200
    assert repo.listar_por_periodo.await_args.kwargs["usuario_id"] == 1
