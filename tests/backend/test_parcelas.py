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

from backend.dependencies import get_session, get_session_begin
from backend.main import app


def _override_session():
    async def _fake():
        yield SimpleNamespace()

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_session_begin] = _fake


def cliente_com(repo):
    _override_session()
    stack = ExitStack()
    stack.enter_context(
        patch("backend.services.parcelas.TransacaoRepository", lambda session: repo)
    )
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


def make_parcela(grupo, numero, total, dia, valor="100.00", descricao="Notebook"):
    return SimpleNamespace(
        grupo_parcela_id=grupo,
        parcela_numero=numero,
        parcela_total=total,
        data=date(2026, 6, dia),
        valor=Decimal(valor),
        descricao=descricao,
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
