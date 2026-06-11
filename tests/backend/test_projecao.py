from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient


@dataclass
class _FakeTransacao:
    tipo: str
    categoria: str
    valor: Decimal
    data: date
    parcela_total: int = 1
    status: str = "PAGO"


class _FakeRepo:
    def __init__(self, transacoes):
        self._transacoes = transacoes

    async def listar_por_periodo(self, inicio, fim):
        return [t for t in self._transacoes if inicio <= t.data <= fim]


def _build_client(monkeypatch, transacoes):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    from backend.dependencies import get_session
    from backend.main import app

    async def _fake_session():
        yield None

    monkeypatch.setattr(
        "backend.controllers.projecao.TransacaoRepository",
        lambda session: _FakeRepo(transacoes),
    )
    app.dependency_overrides[get_session] = _fake_session
    client = TestClient(app)
    return app, client


def _mes_futuro(hoje, meses):
    base = hoje.year * 12 + hoje.month - 1 + meses
    return date(base // 12, base % 12 + 1, 1)


def test_projecao_omite_meses_sem_dados(monkeypatch):
    app, client = _build_client(monkeypatch, [])
    with client:
        resposta = client.get("/api/projecao")
    app.dependency_overrides.clear()

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_projecao_so_traz_meses_com_movimento(monkeypatch):
    from backend.services.graficos import fmt_mes

    hoje = date.today()
    futuro = _mes_futuro(hoje, 3)
    transacoes = [
        _FakeTransacao("GASTO", "COMPRAS", Decimal("100.00"), futuro, parcela_total=3, status="PAGO"),
        _FakeTransacao("GASTO", "COMPRAS", Decimal("100.00"), futuro, parcela_total=3, status="PENDENTE"),
        _FakeTransacao("RECEITA", "RECEITA", Decimal("500.00"), futuro, status="PENDENTE"),
    ]
    app, client = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/projecao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert len(dados) == 1
    alvo = dados[0]
    assert alvo["mes"] == fmt_mes(futuro)
    assert alvo["gastos"] == "200.00"
    assert alvo["receitas"] == "500.00"
    assert alvo["saldo"] == "300.00"
    assert alvo["qtd_parcelas"] == 2


def test_projecao_mantem_qtd_parcelas(monkeypatch):
    hoje = date.today()
    transacoes = [
        _FakeTransacao("GASTO", "COMPRAS", Decimal("50.00"), hoje, parcela_total=1),
        _FakeTransacao("GASTO", "COMPRAS", Decimal("50.00"), hoje, parcela_total=4),
    ]
    app, client = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/projecao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert len(dados) == 1
    assert dados[0]["qtd_parcelas"] == 1
