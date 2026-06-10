"""Testes da API de parcelas ativas do dashboard Flask (T04).

Cenários de specs/dashboard-flask/scenarios/api-parcelas.feature.
Sem DB real: SessionFactory e TransacaoRepository mockados no namespace
do blueprint (dashboard.blueprints.api_parcelas).
"""

import os

for var, valor in {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test",
    "OPENAI_API_KEY": "test",
    "EVOLUTION_API_URL": "http://localhost",
    "EVOLUTION_INSTANCE": "test",
    "EVOLUTION_API_KEY": "test",
    "WHATSAPP_ALLOWED_NUMBER": "5500000000000",
}.items():
    os.environ.setdefault(var, valor)

from contextlib import asynccontextmanager
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from dashboard.app import create_app


class FakeSessionFactory:
    """Suporta `async with SessionFactory() as s` e `async with SessionFactory.begin() as s`."""

    def __init__(self):
        self.session = MagicMock(name="session")

    @asynccontextmanager
    async def _ctx(self):
        yield self.session

    def __call__(self):
        return self._ctx()

    def begin(self):
        return self._ctx()


def fake_transacao(
    grupo_id: str,
    numero: int,
    total: int,
    dias: int,
    valor: str = "199.00",
    descricao: str = "iPhone parcelado",
):
    """Transação fake com data relativa a hoje (hoje + `dias`)."""
    return SimpleNamespace(
        grupo_parcela_id=grupo_id,
        descricao=descricao,
        valor=Decimal(valor),
        parcela_numero=numero,
        parcela_total=total,
        data=date.today() + timedelta(days=dias),
    )


@pytest.fixture
def client_e_repo():
    repo = SimpleNamespace(
        listar_por_periodo=AsyncMock(return_value=[]),
        excluir_grupo=AsyncMock(return_value=0),
    )
    with (
        patch("dashboard.blueprints.api_parcelas.SessionFactory", FakeSessionFactory()),
        patch(
            "dashboard.blueprints.api_parcelas.TransacaoRepository",
            MagicMock(return_value=repo),
        ),
    ):
        app = create_app()
        yield app.test_client(), repo


# --- Cenário: Lista apenas grupos parcelados com parcela futura ---


def test_lista_apenas_grupo_parcelado(client_e_repo):
    client, repo = client_e_repo
    grupo = str(uuid4())
    # parcelas 3..12 futuras (total 12), próxima (nº 3) hoje, demais a cada 30 dias
    parcelas = [fake_transacao(grupo, n, 12, (n - 3) * 30) for n in range(3, 13)]
    avista = fake_transacao(str(uuid4()), 1, 1, 5, valor="50.00", descricao="Coxinha")
    repo.listar_por_periodo.return_value = parcelas + [avista]

    resposta = client.get("/api/parcelas-ativas")

    assert resposta.status_code == 200
    dados = resposta.get_json()
    assert len(dados) == 1
    item = dados[0]
    assert item == {
        "grupo_parcela_id": grupo,
        "descricao": "iPhone parcelado",
        "valor_parcela": "199.00",
        "parcela_numero": 3,
        "parcela_total": 12,
        "proxima_data": date.today().isoformat(),
        "pagas": 2,
    }


def test_consulta_range_futuro_amplo(client_e_repo):
    client, repo = client_e_repo

    resposta = client.get("/api/parcelas-ativas")

    assert resposta.status_code == 200
    assert resposta.get_json() == []
    repo.listar_por_periodo.assert_awaited_once_with(date.today(), date(2030, 12, 31))


def test_valor_parcela_com_duas_casas(client_e_repo):
    client, repo = client_e_repo
    grupo = str(uuid4())
    repo.listar_por_periodo.return_value = [
        fake_transacao(grupo, 1, 3, 0, valor="199"),
    ]

    dados = client.get("/api/parcelas-ativas").get_json()

    assert dados[0]["valor_parcela"] == "199.00"


# --- Cenário: Ordenação por próxima data ---


def test_ordenacao_por_proxima_data(client_e_repo):
    client, repo = client_e_repo
    grupo_longe = str(uuid4())
    grupo_perto = str(uuid4())
    repo.listar_por_periodo.return_value = [
        fake_transacao(grupo_longe, 2, 4, 40, descricao="Notebook"),
        fake_transacao(grupo_longe, 3, 4, 70, descricao="Notebook"),
        fake_transacao(grupo_perto, 5, 10, 10, descricao="Celular"),
        fake_transacao(grupo_perto, 6, 10, 40, descricao="Celular"),
    ]

    dados = client.get("/api/parcelas-ativas").get_json()

    assert [item["grupo_parcela_id"] for item in dados] == [grupo_perto, grupo_longe]
    assert dados[0]["proxima_data"] == (date.today() + timedelta(days=10)).isoformat()
    assert dados[1]["proxima_data"] == (date.today() + timedelta(days=40)).isoformat()


# --- Cenário: Excluir grupo existente ---


def test_excluir_grupo_existente(client_e_repo):
    client, repo = client_e_repo
    repo.excluir_grupo.return_value = 12
    gid = uuid4()

    resposta = client.delete(f"/api/grupos/{gid}")

    assert resposta.status_code == 200
    assert resposta.get_json() == {"ok": True, "removidos": 12}
    repo.excluir_grupo.assert_awaited_once_with(gid)


# --- Cenário: Excluir grupo inexistente ---


def test_excluir_grupo_inexistente(client_e_repo):
    client, repo = client_e_repo
    repo.excluir_grupo.return_value = 0

    resposta = client.delete(f"/api/grupos/{uuid4()}")

    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "Grupo nao encontrado"}


# --- Cenário: UUID inválido ---


def test_uuid_invalido(client_e_repo):
    client, repo = client_e_repo

    resposta = client.delete("/api/grupos/nao-e-uuid")

    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": "ID inválido"}
    repo.excluir_grupo.assert_not_awaited()
