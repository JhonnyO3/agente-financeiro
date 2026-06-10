"""Testes da T02 — API de resumo e pizza de categorias.

Cenarios: specs/dashboard-flask/scenarios/api-resumo.feature
Sem DB real: SessionFactory e TransacaoRepository mockados no namespace
do blueprint (dashboard.blueprints.api_resumo).
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511957818539")

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import TipoEnum
from dashboard.app import create_app


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def fake_session_factory():
    return FakeSession()


def make_fake_repo(transacoes, chamadas=None):
    """Cria classe FakeRepo que devolve `transacoes` e registra (inicio, fim)."""

    class FakeRepo:
        def __init__(self, session):
            self._session = session

        async def listar_por_periodo(self, inicio, fim):
            if chamadas is not None:
                chamadas.append((inicio, fim))
            return transacoes

    return FakeRepo


def transacao(tipo, valor, categoria="OUTROS"):
    return SimpleNamespace(tipo=tipo, valor=Decimal(valor), categoria=categoria)


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _mock_blueprint(monkeypatch, transacoes, chamadas=None):
    monkeypatch.setattr(
        "dashboard.blueprints.api_resumo.SessionFactory", fake_session_factory
    )
    monkeypatch.setattr(
        "dashboard.blueprints.api_resumo.TransacaoRepository",
        make_fake_repo(transacoes, chamadas),
    )


# --- GET /api/resumo ---------------------------------------------------


def test_resumo_soma_por_tipo_com_decimal(client, monkeypatch):
    """Cenario: Resumo soma por tipo com Decimal."""
    _mock_blueprint(
        monkeypatch,
        [
            transacao("GASTO", "100.00"),
            transacao("GASTO", "250.00"),
            transacao("INVESTIMENTO", "500.00"),
        ],
    )

    resp = client.get("/api/resumo?periodo=mes_atual")

    assert resp.status_code == 200
    dados = resp.get_json()
    assert dados["gastos"] == "350.00"
    assert dados["investimentos"] == "500.00"
    assert dados["saldo"] == "150.00"
    assert dados["periodo"] == "mes_atual"


def test_resumo_saldo_negativo(client, monkeypatch):
    """Cenario: Saldo negativo."""
    _mock_blueprint(
        monkeypatch,
        [
            transacao("GASTO", "600.00"),
            transacao("INVESTIMENTO", "100.00"),
        ],
    )

    resp = client.get("/api/resumo")

    assert resp.status_code == 200
    assert resp.get_json()["saldo"] == "-500.00"


def test_resumo_aceita_tipo_como_enum(client, monkeypatch):
    """t.tipo pode vir como enum em vez de str — comparar pelo valor."""
    _mock_blueprint(
        monkeypatch,
        [
            transacao(TipoEnum.GASTO, "75.50"),
            transacao(TipoEnum.INVESTIMENTO, "200.00"),
        ],
    )

    resp = client.get("/api/resumo")

    dados = resp.get_json()
    assert dados["gastos"] == "75.50"
    assert dados["investimentos"] == "200.00"
    assert dados["saldo"] == "124.50"


def test_resumo_sem_transacoes_retorna_zeros(client, monkeypatch):
    _mock_blueprint(monkeypatch, [])

    resp = client.get("/api/resumo")

    dados = resp.get_json()
    assert dados["gastos"] == "0.00"
    assert dados["investimentos"] == "0.00"
    assert dados["saldo"] == "0.00"


def test_resumo_periodo_muda_intervalo_consultado(client, monkeypatch):
    """Mudar ?periodo muda o intervalo passado ao repository."""
    chamadas = []
    _mock_blueprint(monkeypatch, [], chamadas)

    client.get("/api/resumo?periodo=tudo")
    client.get("/api/resumo?periodo=ano_atual")

    inicio_tudo, fim_tudo = chamadas[0]
    inicio_ano, _ = chamadas[1]
    assert inicio_tudo == date(2000, 1, 1)
    assert fim_tudo == date.today()
    assert inicio_ano == date(date.today().year, 1, 1)


def test_resumo_ecoa_periodo_solicitado(client, monkeypatch):
    _mock_blueprint(monkeypatch, [])

    resp = client.get("/api/resumo?periodo=ano_atual")

    assert resp.get_json()["periodo"] == "ano_atual"


# --- GET /api/grafico/categorias ----------------------------------------


def test_categorias_exclui_investimentos_e_zeradas(client, monkeypatch):
    """Cenario: Pizza exclui investimentos e categorias zeradas."""
    _mock_blueprint(
        monkeypatch,
        [
            transacao("GASTO", "150.00", "ALIMENTACAO"),
            transacao("GASTO", "100.00", "TRANSPORTE"),
            transacao("INVESTIMENTO", "999.00", "INVESTIMENTO"),
        ],
    )

    resp = client.get("/api/grafico/categorias")

    assert resp.status_code == 200
    dados = resp.get_json()
    categorias = [item["categoria"] for item in dados]
    assert categorias == ["ALIMENTACAO", "TRANSPORTE"]
    assert dados[0]["total"] == "150.00"
    assert dados[1]["total"] == "100.00"
    soma_percentuais = sum(item["percentual"] for item in dados)
    assert soma_percentuais == pytest.approx(100, abs=0.1)


def test_categorias_ordenado_por_total_decrescente(client, monkeypatch):
    """Cenario: Pizza ordenada por total decrescente."""
    _mock_blueprint(
        monkeypatch,
        [
            transacao("GASTO", "50.00", "LAZER"),
            transacao("GASTO", "300.00", "TRANSPORTE"),
            transacao("GASTO", "120.00", "ALIMENTACAO"),
            transacao("GASTO", "80.00", "ALIMENTACAO"),
        ],
    )

    resp = client.get("/api/grafico/categorias")

    dados = resp.get_json()
    assert [item["categoria"] for item in dados] == [
        "TRANSPORTE",
        "ALIMENTACAO",
        "LAZER",
    ]
    totais = [Decimal(item["total"]) for item in dados]
    assert totais == sorted(totais, reverse=True)


def test_categorias_percentual_float_duas_casas(client, monkeypatch):
    _mock_blueprint(
        monkeypatch,
        [
            transacao("GASTO", "150.00", "ALIMENTACAO"),
            transacao("GASTO", "100.00", "TRANSPORTE"),
            transacao("GASTO", "100.00", "LAZER"),
        ],
    )

    resp = client.get("/api/grafico/categorias")

    dados = resp.get_json()
    por_categoria = {item["categoria"]: item for item in dados}
    assert por_categoria["ALIMENTACAO"]["percentual"] == 42.86
    assert por_categoria["TRANSPORTE"]["percentual"] == 28.57
    assert isinstance(por_categoria["LAZER"]["percentual"], float)


def test_categorias_sem_transacoes_retorna_lista_vazia(client, monkeypatch):
    """Sem gastos nao ha divisao por zero — retorna []."""
    _mock_blueprint(monkeypatch, [transacao("INVESTIMENTO", "500.00", "INVESTIMENTO")])

    resp = client.get("/api/grafico/categorias")

    assert resp.status_code == 200
    assert resp.get_json() == []


def test_categorias_aceita_categoria_como_enum(client, monkeypatch):
    from app.models.enums import CategoriaEnum

    _mock_blueprint(
        monkeypatch,
        [
            SimpleNamespace(
                tipo=TipoEnum.GASTO,
                valor=Decimal("100.00"),
                categoria=CategoriaEnum.ALIMENTACAO,
            )
        ],
    )

    resp = client.get("/api/grafico/categorias")

    dados = resp.get_json()
    assert dados == [
        {"categoria": "ALIMENTACAO", "total": "100.00", "percentual": 100.0}
    ]
