from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@dataclass
class _FakeTransacao:
    tipo: str
    categoria: str
    valor: Decimal
    data: date
    parcela_total: int = 1
    status: str = "PAGO"
    descricao: str = ""
    recorrente: bool = False


class _FakeRepo:
    def __init__(self, transacoes):
        self._transacoes = transacoes

    async def listar_por_periodo(self, inicio, fim, usuario_id=None):
        return [t for t in self._transacoes if inicio <= t.data <= fim]

    async def listar_recorrentes(self, usuario_id=None):
        from backend.services.recorrencia import eh_recorrente

        return [t for t in self._transacoes if eh_recorrente(t)]


def _build_client(monkeypatch, transacoes):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    from backend.auth.dependencies import UsuarioToken, get_usuario_atual
    from backend.dependencies import get_session
    from backend.main import app

    async def _fake_session():
        yield None

    async def _fake_usuario():
        return UsuarioToken(usuario_id=1, role="USER", email="user@exemplo.com")

    monkeypatch.setattr(
        "backend.controllers.graficos.TransacaoRepository",
        lambda session: _FakeRepo(transacoes),
    )
    app.dependency_overrides[get_session] = _fake_session
    app.dependency_overrides[get_usuario_atual] = _fake_usuario
    client = TestClient(app)
    return app, client, get_session


def test_mensal_omite_meses_sem_dados(monkeypatch):
    app, client, get_session = _build_client(monkeypatch, [])
    with client:
        resposta = client.get("/api/grafico/mensal")
    app.dependency_overrides.clear()

    assert resposta.status_code == 200
    assert resposta.json() == []


def test_mensal_retorna_apenas_meses_com_dados_em_ordem(monkeypatch):
    from backend.services.graficos import fmt_mes
    from backend.services.janela import janela_meses

    meses = janela_meses(date.today())
    transacoes = [
        _FakeTransacao("GASTO", "ALIMENTACAO", Decimal("10.00"), meses[6]),
        _FakeTransacao("GASTO", "TRANSPORTE", Decimal("20.00"), meses[8]),
    ]
    app, client, get_session = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/grafico/mensal")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert [d["mes"] for d in dados] == [fmt_mes(meses[6]), fmt_mes(meses[8])]


def test_mensal_soma_por_categoria_gasto(monkeypatch):
    hoje = date.today()
    transacoes = [
        _FakeTransacao("GASTO", "ALIMENTACAO", Decimal("10.50"), hoje),
        _FakeTransacao("GASTO", "ALIMENTACAO", Decimal("4.50"), hoje),
        _FakeTransacao("GASTO", "TRANSPORTE", Decimal("20.00"), hoje),
        _FakeTransacao("RECEITA", "RECEITA", Decimal("999.00"), hoje),
        _FakeTransacao("INVESTIMENTO", "INVESTIMENTO", Decimal("500.00"), hoje),
    ]
    app, client, get_session = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/grafico/mensal")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert len(dados) == 1
    mes_atual = dados[0]
    assert mes_atual["ALIMENTACAO"] == "15.00"
    assert mes_atual["TRANSPORTE"] == "20.00"
    assert "RECEITA" not in mes_atual
    assert "INVESTIMENTO" not in mes_atual


def test_evolucao_inclui_receitas_e_13_meses(monkeypatch):
    hoje = date.today()
    transacoes = [
        _FakeTransacao("GASTO", "ALIMENTACAO", Decimal("30.00"), hoje),
        _FakeTransacao("INVESTIMENTO", "INVESTIMENTO", Decimal("100.00"), hoje),
        _FakeTransacao("RECEITA", "RECEITA", Decimal("200.00"), hoje),
    ]
    app, client, get_session = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/grafico/evolucao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert len(dados) == 13
    for entrada in dados:
        assert "gastos" in entrada
        assert "investimentos" in entrada
        assert "receitas" in entrada
    mes_atual = dados[6]
    assert mes_atual["gastos"] == "30.00"
    assert mes_atual["investimentos"] == "100.00"
    assert mes_atual["receitas"] == "200.00"


def test_evolucao_mes_sem_dados_zero(monkeypatch):
    app, client, get_session = _build_client(monkeypatch, [])
    with client:
        resposta = client.get("/api/grafico/evolucao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert dados[0]["gastos"] == "0.00"
    assert dados[0]["receitas"] == "0.00"
    assert dados[0]["investimentos"] == "0.00"


def test_mensal_projeta_gastos_fixos_nos_meses_futuros(monkeypatch):
    from backend.services.graficos import fmt_mes
    from backend.services.janela import janela_meses

    meses = janela_meses(date.today())
    transacoes = [
        _FakeTransacao("GASTO", "GASTOS_FIXOS", Decimal("100.00"), meses[6], descricao="Internet"),
    ]
    app, client, get_session = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/grafico/mensal")
    app.dependency_overrides.clear()

    dados = {d["mes"]: d for d in resposta.json()}
    assert dados[fmt_mes(meses[6])]["GASTOS_FIXOS"] == "100.00"   # atual: materializado
    assert dados[fmt_mes(meses[7])]["GASTOS_FIXOS"] == "100.00"   # futuro: projetado
    assert dados[fmt_mes(meses[12])]["GASTOS_FIXOS"] == "100.00"  # ultimo futuro: projetado
    assert fmt_mes(meses[5]) not in dados                          # passado: nao projeta


def test_mensal_nao_dobra_fixo_ja_materializado(monkeypatch):
    from backend.services.graficos import fmt_mes
    from backend.services.janela import janela_meses

    meses = janela_meses(date.today())
    transacoes = [
        _FakeTransacao("GASTO", "GASTOS_FIXOS", Decimal("100.00"), meses[6], descricao="Internet"),
        _FakeTransacao("GASTO", "GASTOS_FIXOS", Decimal("100.00"), meses[7], descricao="Internet"),
    ]
    app, client, get_session = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/grafico/mensal")
    app.dependency_overrides.clear()

    dados = {d["mes"]: d for d in resposta.json()}
    assert dados[fmt_mes(meses[7])]["GASTOS_FIXOS"] == "100.00"   # ja materializado, nao soma o template


def test_evolucao_projeta_recorrentes_nos_meses_futuros(monkeypatch):
    from backend.services.janela import janela_meses

    meses = janela_meses(date.today())
    transacoes = [
        _FakeTransacao("GASTO", "GASTOS_FIXOS", Decimal("100.00"), meses[6], descricao="Internet"),
    ]
    app, client, get_session = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/grafico/evolucao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert dados[6]["gastos"] == "100.00"   # atual: materializado
    assert dados[7]["gastos"] == "100.00"   # futuro: projetado
    assert dados[5]["gastos"] == "0.00"     # passado: nao projeta


def test_evolucao_projeta_receita_recorrente_marcada(monkeypatch):
    from backend.services.janela import janela_meses

    meses = janela_meses(date.today())
    transacoes = [
        _FakeTransacao("RECEITA", "RECEITA", Decimal("5000.00"), meses[6], descricao="Salario", recorrente=True),
    ]
    app, client, get_session = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/grafico/evolucao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert dados[6]["receitas"] == "5000.00"   # atual: materializado
    assert dados[7]["receitas"] == "5000.00"   # futuro: salario projetado
