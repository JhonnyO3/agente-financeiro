"""Testes da T06 — API de projeção de pendentes (6 meses).

Cenarios: specs/melhorias-dashboard/scenarios/06-api-resumo-projecao.feature
Contrato: specs/melhorias-dashboard/contracts/api-json-v2.md (congelado)
Sem DB real: SessionFactory e TransacaoRepository mockados no namespace
do blueprint (dashboard.blueprints.api_projecao).
"""

import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511957818539")

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import StatusEnum, TipoEnum
from dashboard.app import create_app

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def label_mes(d: date) -> str:
    """Mesmo formato 'Jun/26' do grafico mensal (api_graficos.fmt_mes)."""
    return f"{MESES_PT[d.month - 1]}/{str(d.year)[2:]}"


def primeiro_dia_mes(meses_a_frente: int) -> date:
    """Primeiro dia do mes corrente + N meses (relativo a date.today())."""
    hoje = date.today()
    base = hoje.year * 12 + hoje.month - 1 + meses_a_frente
    return date(base // 12, base % 12 + 1, 1)


def ultimo_dia_mes(meses_a_frente: int) -> date:
    return primeiro_dia_mes(meses_a_frente + 1) - timedelta(days=1)


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


def transacao(tipo, valor, data, status="PENDENTE", parcela_total=1):
    return SimpleNamespace(
        tipo=tipo,
        valor=Decimal(valor),
        data=data,
        status=status,
        parcela_total=parcela_total,
    )


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def _mock_blueprint(monkeypatch, transacoes, chamadas=None):
    monkeypatch.setattr(
        "dashboard.blueprints.api_projecao.SessionFactory", fake_session_factory
    )
    monkeypatch.setattr(
        "dashboard.blueprints.api_projecao.TransacaoRepository",
        make_fake_repo(transacoes, chamadas),
    )


# --- GET /api/projecao ---------------------------------------------------


def test_projecao_sem_dados_retorna_6_meses_zerados(client, monkeypatch):
    """Cenario: Mes vazio vem zerado — sempre 6 elementos."""
    _mock_blueprint(monkeypatch, [])

    resp = client.get("/api/projecao")

    assert resp.status_code == 200
    dados = resp.get_json()
    assert len(dados) == 6
    for i, item in enumerate(dados):
        assert item == {
            "mes": label_mes(primeiro_dia_mes(i)),
            "gastos_pendentes": "0.00",
            "receitas_pendentes": "0.00",
            "saldo_projetado": "0.00",
            "qtd_parcelas": 0,
        }


def test_projecao_ordem_cronologica_do_mes_corrente(client, monkeypatch):
    """Primeiro elemento e o mes corrente; demais em ordem crescente."""
    _mock_blueprint(monkeypatch, [])

    dados = client.get("/api/projecao").get_json()

    labels = [item["mes"] for item in dados]
    assert labels == [label_mes(primeiro_dia_mes(i)) for i in range(6)]


def test_projecao_consulta_mes_atual_ate_fim_do_mes_mais_5(client, monkeypatch):
    """Intervalo: primeiro dia do mes atual ate o ultimo dia do mes corrente+5."""
    chamadas = []
    _mock_blueprint(monkeypatch, [], chamadas)

    client.get("/api/projecao")

    assert chamadas == [(primeiro_dia_mes(0), ultimo_dia_mes(5))]


def test_projecao_ignora_query_param_periodo(client, monkeypatch):
    chamadas = []
    _mock_blueprint(monkeypatch, [], chamadas)

    resp = client.get("/api/projecao?periodo=tudo")

    assert resp.status_code == 200
    assert chamadas == [(primeiro_dia_mes(0), ultimo_dia_mes(5))]
    assert len(resp.get_json()) == 6


def test_projecao_so_considera_pendentes(client, monkeypatch):
    """Cenario: Projecao so com pendentes — PAGO nao entra nas somas."""
    _mock_blueprint(
        monkeypatch,
        [
            transacao("GASTO", "200.00", primeiro_dia_mes(1), status="PENDENTE", parcela_total=3),
            transacao("GASTO", "300.00", primeiro_dia_mes(2), status="PENDENTE", parcela_total=3),
            transacao("GASTO", "999.00", primeiro_dia_mes(1), status="PAGO", parcela_total=3),
        ],
    )

    dados = client.get("/api/projecao").get_json()

    assert len(dados) == 6
    assert dados[1]["gastos_pendentes"] == "200.00"
    assert dados[1]["qtd_parcelas"] == 1
    assert dados[2]["gastos_pendentes"] == "300.00"
    assert dados[2]["qtd_parcelas"] == 1


def test_projecao_saldo_projetado_negativo(client, monkeypatch):
    """Cenario: Saldo projetado negativo — mes futuro so com gastos 750."""
    _mock_blueprint(
        monkeypatch,
        [transacao("GASTO", "750.00", primeiro_dia_mes(1))],
    )

    dados = client.get("/api/projecao").get_json()

    assert dados[1]["gastos_pendentes"] == "750.00"
    assert dados[1]["receitas_pendentes"] == "0.00"
    assert dados[1]["saldo_projetado"] == "-750.00"


def test_projecao_saldo_projetado_receitas_menos_gastos(client, monkeypatch):
    _mock_blueprint(
        monkeypatch,
        [
            transacao("GASTO", "400.00", primeiro_dia_mes(2)),
            transacao("RECEITA", "1000.00", primeiro_dia_mes(2)),
            transacao("INVESTIMENTO", "5000.00", primeiro_dia_mes(2)),
        ],
    )

    dados = client.get("/api/projecao").get_json()

    assert dados[2]["gastos_pendentes"] == "400.00"
    assert dados[2]["receitas_pendentes"] == "1000.00"
    assert dados[2]["saldo_projetado"] == "600.00"


def test_projecao_qtd_parcelas_conta_so_parcelados(client, monkeypatch):
    """qtd_parcelas = registros PENDENTEs com parcela_total > 1 no mes."""
    _mock_blueprint(
        monkeypatch,
        [
            transacao("GASTO", "100.00", primeiro_dia_mes(1), parcela_total=3),
            transacao("GASTO", "100.00", primeiro_dia_mes(1), parcela_total=12),
            transacao("GASTO", "50.00", primeiro_dia_mes(1), parcela_total=1),
            transacao("RECEITA", "80.00", primeiro_dia_mes(1), parcela_total=2),
        ],
    )

    dados = client.get("/api/projecao").get_json()

    assert dados[1]["qtd_parcelas"] == 3
    assert dados[1]["gastos_pendentes"] == "250.00"
    assert dados[1]["receitas_pendentes"] == "80.00"


def test_projecao_aceita_status_e_tipo_como_enum(client, monkeypatch):
    """status/tipo podem vir como enum do ORM — comparar pelo valor."""
    _mock_blueprint(
        monkeypatch,
        [
            transacao(TipoEnum.GASTO, "120.00", primeiro_dia_mes(0), status=StatusEnum.PENDENTE, parcela_total=2),
            transacao(TipoEnum.GASTO, "999.00", primeiro_dia_mes(0), status=StatusEnum.PAGO),
        ],
    )

    dados = client.get("/api/projecao").get_json()

    assert dados[0]["gastos_pendentes"] == "120.00"
    assert dados[0]["saldo_projetado"] == "-120.00"
    assert dados[0]["qtd_parcelas"] == 1
