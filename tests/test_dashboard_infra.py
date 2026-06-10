"""Testes da infraestrutura do dashboard Flask (T01).

Cenários de specs/dashboard-flask/scenarios/periodo.feature.
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

from datetime import date, timedelta
from unittest.mock import patch

from dashboard.app import create_app
from dashboard.periodo import DATA_PISO, PERIODOS_VALIDOS, resolver_periodo


class DataFixa(date):
    """Subclasse de date com today() fixo em 2026-06-10."""

    @classmethod
    def today(cls):
        return cls(2026, 6, 10)


# --- Cenário: Período mês atual ---


def test_periodo_mes_atual():
    with patch("dashboard.periodo.date", DataFixa):
        inicio, fim = resolver_periodo("mes_atual")
    assert inicio == date(2026, 6, 1)
    assert fim == date(2026, 6, 10)


# --- Cenário: Período mês anterior ---


def test_periodo_mes_anterior():
    with patch("dashboard.periodo.date", DataFixa):
        inicio, fim = resolver_periodo("mes_anterior")
    assert inicio == date(2026, 5, 1)
    assert fim == date(2026, 5, 31)


def test_periodo_mes_anterior_virada_de_ano():
    class Janeiro(date):
        @classmethod
        def today(cls):
            return cls(2026, 1, 15)

    with patch("dashboard.periodo.date", Janeiro):
        inicio, fim = resolver_periodo("mes_anterior")
    assert inicio == date(2025, 12, 1)
    assert fim == date(2025, 12, 31)


# --- Cenário: Período tudo usa o piso ---


def test_periodo_tudo_usa_piso():
    inicio, fim = resolver_periodo("tudo")
    assert inicio == date(2000, 1, 1)
    assert fim == date.today()


def test_data_piso_constante():
    assert DATA_PISO == date(2000, 1, 1)


# --- Cenário: Período inválido usa fallback seguro ---


def test_periodo_invalido_usa_fallback_mes_atual():
    resultado = resolver_periodo("banana")
    assert resultado == resolver_periodo("mes_atual")


# --- Demais mapeamentos do contrato periodo.md ---


def test_periodo_ultimos_3_meses():
    with patch("dashboard.periodo.date", DataFixa):
        inicio, fim = resolver_periodo("ultimos_3_meses")
    assert inicio == date(2026, 6, 10) - timedelta(days=90)
    assert fim == date(2026, 6, 10)


def test_periodo_ultimos_6_meses():
    with patch("dashboard.periodo.date", DataFixa):
        inicio, fim = resolver_periodo("ultimos_6_meses")
    assert inicio == date(2026, 6, 10) - timedelta(days=180)
    assert fim == date(2026, 6, 10)


def test_periodo_ano_atual():
    with patch("dashboard.periodo.date", DataFixa):
        inicio, fim = resolver_periodo("ano_atual")
    assert inicio == date(2026, 1, 1)
    assert fim == date(2026, 6, 10)


def test_periodos_validos():
    assert PERIODOS_VALIDOS == frozenset(
        {
            "mes_atual",
            "mes_anterior",
            "ultimos_3_meses",
            "ultimos_6_meses",
            "ano_atual",
            "tudo",
        }
    )


# --- Cenário: Health check ---


def test_health_check():
    app = create_app()
    client = app.test_client()
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.get_json() == {"ok": True}


def test_create_app_sobe_sem_blueprints():
    """Os módulos de blueprint (T02-T05) ainda não existem; a app sobe mesmo assim."""
    app = create_app()
    assert app is not None
