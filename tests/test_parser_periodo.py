"""Tests for parsear_periodo — TDD, no real network/DB/LLM."""

from datetime import date, datetime, timezone

from agent.services.relogio import Relogio


def _relogio(ano: int, mes: int, dia: int) -> Relogio:
    fixed = datetime(ano, mes, dia, 12, 0, 0, tzinfo=timezone.utc)
    return Relogio("America/Sao_Paulo", _fixed=fixed)


# ---------------------------------------------------------------------------
# Imports deferred so tests can be collected even before implementation exists
# ---------------------------------------------------------------------------


def _parsear(periodo, relogio):  # type: ignore[no-untyped-def]
    from agent.services.parser_periodo import parsear_periodo

    return parsear_periodo(periodo, relogio)


# ---------------------------------------------------------------------------
# hoje / ontem
# ---------------------------------------------------------------------------


def test_hoje():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("hoje", r)
    assert inicio == date(2026, 6, 15)
    assert fim == date(2026, 6, 15)
    assert label == "hoje"


def test_ontem():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("ontem", r)
    assert inicio == date(2026, 6, 14)
    assert fim == date(2026, 6, 14)
    assert label == "ontem"


# ---------------------------------------------------------------------------
# semana_atual / semana_passada
# ---------------------------------------------------------------------------


def test_semana_atual_segunda():
    # 15/06/2026 é segunda-feira
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("semana_atual", r)
    assert inicio == date(2026, 6, 15)
    assert fim == date(2026, 6, 21)
    assert label == "semana atual"


def test_semana_atual_domingo():
    # 21/06/2026 é domingo — ainda devolve seg–dom da semana corrente
    r = _relogio(2026, 6, 21)
    inicio, fim, label = _parsear("semana_atual", r)
    assert inicio == date(2026, 6, 15)
    assert fim == date(2026, 6, 21)
    assert label == "semana atual"


def test_semana_passada():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("semana_passada", r)
    assert inicio == date(2026, 6, 8)
    assert fim == date(2026, 6, 14)
    assert label == "semana passada"


# ---------------------------------------------------------------------------
# mes_atual / None / mes_passado
# ---------------------------------------------------------------------------


def test_mes_atual_explicito():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("mes_atual", r)
    assert inicio == date(2026, 6, 1)
    assert fim == date(2026, 6, 30)
    assert label == "Jun/2026"


def test_mes_atual_none():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear(None, r)
    assert inicio == date(2026, 6, 1)
    assert fim == date(2026, 6, 30)
    assert label == "Jun/2026"


def test_mes_passado():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("mes_passado", r)
    assert inicio == date(2026, 5, 1)
    assert fim == date(2026, 5, 31)
    assert label == "Mai/2026"


def test_mes_passado_virada_de_ano():
    r = _relogio(2026, 1, 10)
    inicio, fim, label = _parsear("mes_passado", r)
    assert inicio == date(2025, 12, 1)
    assert fim == date(2025, 12, 31)
    assert label == "Dez/2025"


# ---------------------------------------------------------------------------
# YYYY-MM
# ---------------------------------------------------------------------------


def test_yyyy_mm():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("2026-05", r)
    assert inicio == date(2026, 5, 1)
    assert fim == date(2026, 5, 31)
    assert label == "Mai/2026"


def test_yyyy_mm_invalido_fallback():
    r = _relogio(2026, 6, 15)
    # Mês 13 não existe — deve cair em fallback sem exceção
    inicio, fim, label = _parsear("2026-13", r)
    assert inicio == date(2026, 6, 1)
    assert fim == date(2026, 6, 30)
    assert label == "Jun/2026"


# ---------------------------------------------------------------------------
# YYYY-MM-DD
# ---------------------------------------------------------------------------


def test_yyyy_mm_dd():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("2026-06-15", r)
    assert inicio == date(2026, 6, 15)
    assert fim == date(2026, 6, 15)
    assert label == "15/06/2026"


# ---------------------------------------------------------------------------
# nomes de mês em PT
# ---------------------------------------------------------------------------


def test_nome_mes_junho():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("junho", r)
    assert inicio == date(2026, 6, 1)
    assert fim == date(2026, 6, 30)
    assert label == "Jun/2026"


def test_nome_mes_marco_com_acento():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("março", r)
    assert inicio == date(2026, 3, 1)
    assert fim == date(2026, 3, 31)
    assert label == "Mar/2026"


def test_nome_mes_marco_sem_acento():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("marco", r)
    assert inicio == date(2026, 3, 1)
    assert fim == date(2026, 3, 31)
    assert label == "Mar/2026"


# ---------------------------------------------------------------------------
# fallback para entradas inválidas
# ---------------------------------------------------------------------------


def test_valor_invalido_fallback():
    r = _relogio(2026, 6, 15)
    inicio, fim, label = _parsear("valor_invalido", r)
    assert inicio == date(2026, 6, 1)
    assert fim == date(2026, 6, 30)
    assert label == "Jun/2026"


def test_valor_invalido_nao_levanta_excecao():
    r = _relogio(2026, 6, 15)
    # Must not raise any exception
    result = _parsear("qualquer_coisa_maluca_123", r)
    assert len(result) == 3


def test_fallback_inicio_menor_igual_fim():
    r = _relogio(2026, 6, 15)
    inicio, fim, _ = _parsear("totalmente_errado", r)
    assert inicio <= fim
