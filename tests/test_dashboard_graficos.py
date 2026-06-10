"""Testes dos endpoints de gráficos temporais do dashboard (T03).

Cenários de specs/dashboard-flask/scenarios/api-graficos.feature.
Sem DB real: SessionFactory e TransacaoRepository são mockados no
namespace do blueprint. Datas construídas relativas a date.today()
para serem determinísticas em qualquer mês de execução.
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

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import CategoriaEnum, TipoEnum
from dashboard.app import create_app

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

CATEGORIAS_GASTO = (
    "ALIMENTACAO",
    "TRANSPORTE",
    "LAZER",
    "EDUCACAO",
    "GASTOS_FIXOS",
    "COMPRAS",
    "GASTOS_PONTUAIS",
)


def label(d: date) -> str:
    return f"{MESES_PT[d.month - 1]}/{str(d.year)[2:]}"


def primeiro_dia_meses_atras(n: int) -> date:
    """Primeiro dia do mês, n meses atrás (n=0 → mês atual)."""
    hoje = date.today()
    total = hoje.year * 12 + hoje.month - 1 - n
    return date(total // 12, total % 12 + 1, 1)


def transacao(data, valor, tipo="GASTO", categoria="ALIMENTACAO"):
    return SimpleNamespace(
        data=data, valor=Decimal(valor), tipo=tipo, categoria=categoria
    )


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def montar_client(monkeypatch):
    """Devolve (test_client, chamadas) com repository fake servindo `transacoes`."""

    def _montar(transacoes):
        chamadas = []

        class FakeRepo:
            def __init__(self, session):
                pass

            async def listar_por_periodo(self, inicio, fim):
                chamadas.append((inicio, fim))
                return [t for t in transacoes if inicio <= t.data <= fim]

        monkeypatch.setattr(
            "dashboard.blueprints.api_graficos.SessionFactory", FakeSession
        )
        monkeypatch.setattr(
            "dashboard.blueprints.api_graficos.TransacaoRepository", FakeRepo
        )
        return create_app().test_client(), chamadas

    return _montar


# --- Cenário: Mensal sempre retorna 6 meses ---


def test_mensal_retorna_6_meses_ordem_crescente(montar_client):
    """Gastos em apenas 2 dos últimos 6 meses → ainda assim 6 elementos."""
    client, _ = montar_client(
        [
            transacao(primeiro_dia_meses_atras(3), "200.00", categoria="ALIMENTACAO"),
            transacao(primeiro_dia_meses_atras(0), "80.50", categoria="TRANSPORTE"),
        ]
    )
    resposta = client.get("/api/grafico/mensal")
    assert resposta.status_code == 200
    corpo = resposta.get_json()

    assert len(corpo) == 6
    labels_esperados = [label(primeiro_dia_meses_atras(n)) for n in range(5, -1, -1)]
    assert [item["mes"] for item in corpo] == labels_esperados


def test_mensal_todas_as_7_categorias_com_zero_onde_nao_ha_dados(montar_client):
    client, _ = montar_client(
        [transacao(primeiro_dia_meses_atras(0), "200.00", categoria="ALIMENTACAO")]
    )
    corpo = client.get("/api/grafico/mensal").get_json()

    for item in corpo:
        assert set(item.keys()) == {"mes", *CATEGORIAS_GASTO}
        assert "INVESTIMENTO" not in item

    # mês atual (último elemento) tem a soma; demais meses tudo "0.00"
    assert corpo[-1]["ALIMENTACAO"] == "200.00"
    assert corpo[-1]["TRANSPORTE"] == "0.00"
    for item in corpo[:-1]:
        for cat in CATEGORIAS_GASTO:
            assert item[cat] == "0.00"


def test_mensal_soma_por_categoria_com_decimal(montar_client):
    mes_passado = primeiro_dia_meses_atras(1)
    client, _ = montar_client(
        [
            transacao(mes_passado, "10.10", categoria="LAZER"),
            transacao(mes_passado, "20.20", categoria="LAZER"),
            transacao(mes_passado, "5.00", categoria="COMPRAS"),
        ]
    )
    corpo = client.get("/api/grafico/mensal").get_json()
    item = corpo[-2]  # mês anterior
    assert item["LAZER"] == "30.30"
    assert item["COMPRAS"] == "5.00"


# --- Cenário: Mensal ignora o período e investimentos ---


def test_mensal_ignora_periodo_e_investimentos(montar_client):
    client, chamadas = montar_client(
        [
            transacao(
                primeiro_dia_meses_atras(0),
                "500.00",
                tipo="INVESTIMENTO",
                categoria="INVESTIMENTO",
            )
        ]
    )
    corpo = client.get("/api/grafico/mensal?periodo=tudo").get_json()

    # ignora ?periodo: consulta sempre os últimos 6 meses, não desde 2000
    assert chamadas == [(primeiro_dia_meses_atras(5), date.today())]

    # investimento não entra em nenhuma soma
    assert len(corpo) == 6
    for item in corpo:
        for cat in CATEGORIAS_GASTO:
            assert item[cat] == "0.00"


# --- Cenário: Label de mês em português ---


def test_label_mes_em_portugues(montar_client):
    hoje = date.today()
    client, _ = montar_client(
        [transacao(hoje.replace(day=1), "50.00", categoria="ALIMENTACAO")]
    )
    corpo = client.get("/api/grafico/mensal").get_json()
    # ex.: junho/2026 → "Jun/26": 3 letras + "/" + 2 dígitos do ano
    assert corpo[-1]["mes"] == label(hoje)
    assert len(corpo[-1]["mes"]) == 6
    assert corpo[-1]["mes"][3] == "/"


def test_mensal_aceita_tipo_e_categoria_como_enum(montar_client):
    """t.tipo/t.categoria podem vir como enum do ORM — comparar por valor."""
    client, _ = montar_client(
        [
            transacao(
                primeiro_dia_meses_atras(0),
                "75.00",
                tipo=TipoEnum.GASTO,
                categoria=CategoriaEnum.TRANSPORTE,
            ),
            transacao(
                primeiro_dia_meses_atras(0),
                "999.00",
                tipo=TipoEnum.INVESTIMENTO,
                categoria=CategoriaEnum.INVESTIMENTO,
            ),
        ]
    )
    corpo = client.get("/api/grafico/mensal").get_json()
    assert corpo[-1]["TRANSPORTE"] == "75.00"
    assert all(item.get("INVESTIMENTO") is None for item in corpo)


# --- Cenário: Evolução só traz meses com dados ---


def test_evolucao_so_meses_com_dados(montar_client):
    dois_meses_atras = primeiro_dia_meses_atras(2)
    mes_atual = primeiro_dia_meses_atras(0)
    client, chamadas = montar_client(
        [
            transacao(dois_meses_atras, "350.00"),
            transacao(mes_atual, "120.00"),
            transacao(
                mes_atual, "500.00", tipo="INVESTIMENTO", categoria="INVESTIMENTO"
            ),
        ]
    )
    resposta = client.get("/api/grafico/evolucao")
    assert resposta.status_code == 200
    corpo = resposta.get_json()

    # busca desde o piso 2000-01-01 até hoje
    assert chamadas == [(date(2000, 1, 1), date.today())]

    # apenas os 2 meses com registros, em ordem cronológica crescente
    assert len(corpo) == 2
    assert corpo[0] == {
        "mes": label(dois_meses_atras),
        "gastos": "350.00",
        "investimentos": "0.00",
    }
    assert corpo[1] == {
        "mes": label(mes_atual),
        "gastos": "120.00",
        "investimentos": "500.00",
    }


def test_evolucao_sem_dados_retorna_lista_vazia(montar_client):
    client, _ = montar_client([])
    corpo = client.get("/api/grafico/evolucao").get_json()
    assert corpo == []
