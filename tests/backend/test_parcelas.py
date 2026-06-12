import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test"
)

from contextlib import ExitStack
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session, get_session_begin
from backend.main import app


def _override_session():
    async def _fake():
        yield SimpleNamespace()

    async def _fake_usuario():
        return UsuarioToken(usuario_id=1, role="USER", email="user@exemplo.com")

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_session_begin] = _fake
    app.dependency_overrides[get_usuario_atual] = _fake_usuario


def cliente_com(repo):
    _override_session()
    stack = ExitStack()
    stack.enter_context(
        patch("backend.services.parcelas.TransacaoRepository", lambda session: repo)
    )
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


def make_parcela(grupo, numero, total, dia, valor="100.00", descricao="Notebook", status="PENDENTE", mes=6):
    return SimpleNamespace(
        grupo_parcela_id=grupo,
        parcela_numero=numero,
        parcela_total=total,
        data=date(2026, mes, dia),
        valor=Decimal(valor),
        descricao=descricao,
        status=status,
    )


def test_parcelas_ativas_agrupa_e_pega_proxima():
    grupo = "grupo-a"
    transacoes = [
        make_parcela(grupo, 3, 5, dia=10),
        make_parcela(grupo, 4, 5, dia=20),
    ]
    repo = SimpleNamespace(
        listar_por_periodo=AsyncMock(return_value=transacoes)
    )
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/parcelas-ativas")

    assert resposta.status_code == 200
    itens = resposta.json()
    assert len(itens) == 1
    item = itens[0]
    assert item["grupo_parcela_id"] == grupo
    assert item["descricao"] == "Notebook"
    assert item["valor_parcela"] == "100.00"
    assert item["parcela_numero"] == 3
    assert item["parcela_total"] == 5
    assert item["proxima_data"] == "2026-06-10"
    assert item["pagas"] == 2


def test_parcelas_ativas_proxima_e_a_pendente_nao_a_paga():
    grupo = "carro"
    transacoes = [
        make_parcela(grupo, 11, 12, dia=10, mes=6, status="PAGO", valor="1200.00"),
        make_parcela(grupo, 12, 12, dia=10, mes=7, status="PENDENTE", valor="1200.00"),
    ]
    repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/parcelas-ativas")

    itens = resposta.json()
    assert len(itens) == 1
    item = itens[0]
    assert item["parcela_numero"] == 12
    assert item["proxima_data"] == "2026-07-10"
    assert item["pagas"] == 11


def test_parcelas_ativas_grupo_todo_pago_some():
    transacoes = [
        make_parcela("quitado", 4, 4, dia=10, status="PAGO"),
    ]
    repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/parcelas-ativas")

    assert resposta.json() == []


def test_parcelas_ativas_ignora_nao_parceladas():
    transacoes = [
        make_parcela("g1", 1, 1, dia=5),
        make_parcela("g2", 2, 3, dia=8),
    ]
    repo = SimpleNamespace(
        listar_por_periodo=AsyncMock(return_value=transacoes)
    )
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/parcelas-ativas")

    itens = resposta.json()
    assert {i["grupo_parcela_id"] for i in itens} == {"g2"}


def test_parcelas_ativas_ordena_por_proxima_data():
    transacoes = [
        make_parcela("g1", 2, 4, dia=25),
        make_parcela("g2", 2, 4, dia=5),
    ]
    repo = SimpleNamespace(
        listar_por_periodo=AsyncMock(return_value=transacoes)
    )
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/parcelas-ativas")

    datas = [i["proxima_data"] for i in resposta.json()]
    assert datas == ["2026-06-05", "2026-06-25"]


def test_excluir_grupo_ok():
    repo = SimpleNamespace(excluir_grupo=AsyncMock(return_value=3))
    client, stack = cliente_com(repo)
    grupo = str(uuid4())
    with stack:
        resposta = client.delete(f"/api/grupos/{grupo}")

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True, "removidos": 3}


def test_excluir_grupo_id_invalido_400():
    repo = SimpleNamespace(excluir_grupo=AsyncMock(return_value=0))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.delete("/api/grupos/nao-e-uuid")

    assert resposta.status_code == 400
    assert resposta.json() == {"erro": "ID inválido"}
    repo.excluir_grupo.assert_not_awaited()


def test_excluir_grupo_inexistente_404():
    repo = SimpleNamespace(excluir_grupo=AsyncMock(return_value=0))
    client, stack = cliente_com(repo)
    grupo = str(uuid4())
    with stack:
        resposta = client.delete(f"/api/grupos/{grupo}")

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "Grupo nao encontrado"}


# ---------------------------------------------------------------------------
# RF-01: listar_ativas deve incluir pendentes vencidas (piso = date(2000,1,1))
# Cenários: specs/parcelas-assinaturas/scenarios/01-base-datas-repositorio.feature
# ---------------------------------------------------------------------------


def test_listar_ativas_inclui_pendente_vencida():
    """
    Cenário: listar_ativas inclui grupo com parcela pendente vencida.

    Antes do RF-01 listar_por_periodo era chamada com date.today() como início,
    o que excluía datas passadas. Após o fix, o piso passa a date(2000, 1, 1),
    então uma parcela PENDENTE com data no passado deve aparecer.
    """
    grupo = "grupo-vencido"
    # parcela com data no passado e status PENDENTE — deve aparecer
    transacoes = [
        make_parcela(grupo, 2, 3, dia=1, mes=5, status="PENDENTE"),   # 2026-05-01 (passado)
        make_parcela(grupo, 3, 3, dia=1, mes=6, status="PENDENTE"),   # 2026-06-01 (passado)
    ]
    repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/parcelas-ativas")

    assert resposta.status_code == 200
    itens = resposta.json()
    grupos_ids = {i["grupo_parcela_id"] for i in itens}
    assert grupo in grupos_ids, (
        "Grupo com parcela PENDENTE vencida deveria aparecer em listar_ativas (RF-01)"
    )


def test_listar_ativas_inicio_janela_e_date_2000_1_1():
    """
    Verifica que listar_por_periodo é chamada com date(2000, 1, 1) como início
    (e não date.today()), conforme exigido pelo RF-01.
    """
    repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=[]))
    client, stack = cliente_com(repo)
    with stack:
        client.get("/api/parcelas-ativas")

    repo.listar_por_periodo.assert_awaited_once()
    inicio_usado = repo.listar_por_periodo.call_args[0][0]
    assert inicio_usado == date(2000, 1, 1), (
        f"listar_por_periodo deveria ser chamada com date(2000,1,1) mas foi chamada com {inicio_usado}"
    )


def test_listar_ativas_grupo_totalmente_pago_nao_aparece():
    """
    Cenário: listar_ativas exclui grupo totalmente pago.
    Regressão — garante que o comportamento existente não foi quebrado pelo RF-01.
    """
    grupo = "grupo-quitado"
    transacoes = [
        make_parcela(grupo, 1, 3, dia=1, mes=1, status="PAGO"),
        make_parcela(grupo, 2, 3, dia=1, mes=2, status="PAGO"),
        make_parcela(grupo, 3, 3, dia=1, mes=3, status="PAGO"),
    ]
    repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/parcelas-ativas")

    assert resposta.status_code == 200
    itens = resposta.json()
    grupos_ids = {i["grupo_parcela_id"] for i in itens}
    assert grupo not in grupos_ids, "Grupo totalmente pago não deveria aparecer em listar_ativas"
