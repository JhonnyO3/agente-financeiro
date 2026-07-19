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
    descricao: str = ""
    recorrente: bool = False


class _FakeRepo:
    def __init__(self, transacoes):
        self._transacoes = transacoes

    async def listar_por_periodo(self, inicio, fim, usuario_id=None):
        return [t for t in self._transacoes if inicio <= t.data <= fim]

    async def listar_recorrentes(self, usuario_id=None):
        return [t for t in self._transacoes if getattr(t, "recorrente", False)]


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
        "backend.controllers.projecao.TransacaoRepository",
        lambda session: _FakeRepo(transacoes),
    )
    app.dependency_overrides[get_session] = _fake_session
    app.dependency_overrides[get_usuario_atual] = _fake_usuario
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


def test_projecao_ignora_meses_passados(monkeypatch):
    from backend.services.graficos import fmt_mes

    hoje = date.today()
    passado = _mes_futuro(hoje, -2)
    futuro = _mes_futuro(hoje, 2)
    transacoes = [
        _FakeTransacao("GASTO", "COMPRAS", Decimal("10.00"), passado),
        _FakeTransacao("GASTO", "COMPRAS", Decimal("20.00"), futuro),
    ]
    app, client = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/projecao")
    app.dependency_overrides.clear()

    meses = [linha["mes"] for linha in resposta.json()]
    assert fmt_mes(passado) not in meses
    assert fmt_mes(futuro) in meses


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


def _linha(dados, mes_str):
    return next(linha for linha in dados if linha["mes"] == mes_str)


def test_projecao_mes_so_com_parcela_materializada(monkeypatch):
    from backend.services.graficos import fmt_mes

    hoje = date.today()
    futuro = _mes_futuro(hoje, 2)
    transacoes = [
        _FakeTransacao(
            "GASTO", "COMPRAS", Decimal("500.00"), futuro,
            parcela_total=3, descricao="Notebook",
        ),
    ]
    app, client = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/projecao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    assert len(dados) == 1
    assert dados[0]["mes"] == fmt_mes(futuro)
    assert dados[0]["gastos"] == "500.00"
    assert dados[0]["qtd_parcelas"] == 1


def test_projecao_recorrencia_materializada_conta_como_transacao_real(monkeypatch):
    from backend.services.graficos import fmt_mes

    hoje = date.today()
    futuro = _mes_futuro(hoje, 2)
    transacoes = [
        _FakeTransacao(
            "GASTO", "GASTOS_FIXOS", Decimal("1000.00"), futuro,
            descricao="Aluguel",
        ),
    ]
    app, client = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/projecao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    linha = _linha(dados, fmt_mes(futuro))
    assert linha["gastos"] == "1000.00"
    assert linha["saldo"] == "-1000.00"
    assert linha["qtd_parcelas"] == 0


def test_projecao_nao_projeta_recorrente_do_passado(monkeypatch):
    from backend.services.graficos import fmt_mes

    hoje = date.today()
    passado = _mes_futuro(hoje, -3)
    futuro = _mes_futuro(hoje, 2)
    transacoes = [
        _FakeTransacao(
            "GASTO", "GASTOS_FIXOS", Decimal("1200.00"), passado,
            descricao="Aluguel", recorrente=True,
        ),
    ]
    app, client = _build_client(monkeypatch, transacoes)
    with client:
        resposta = client.get("/api/projecao")
    app.dependency_overrides.clear()

    dados = resposta.json()
    meses = [linha["mes"] for linha in dados]
    assert fmt_mes(futuro) not in meses
