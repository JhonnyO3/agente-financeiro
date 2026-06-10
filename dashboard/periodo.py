"""Resolução de período para os endpoints do dashboard.

Contrato: specs/dashboard-flask/contracts/periodo.md (congelado).
"""

from datetime import date, timedelta

DATA_PISO = date(2000, 1, 1)  # consistente com o agente

PERIODOS_VALIDOS = frozenset(
    {
        "mes_atual",
        "mes_anterior",
        "ultimos_3_meses",
        "ultimos_6_meses",
        "ano_atual",
        "tudo",
    }
)


def resolver_periodo(periodo: str) -> tuple[date, date]:
    """Converte o query param `periodo` em `(inicio, fim)`.

    Valor inválido usa fallback seguro: `mes_atual`.
    """
    hoje = date.today()

    if periodo == "mes_anterior":
        primeiro_mes_atual = date(hoje.year, hoje.month, 1)
        ultimo_mes_anterior = primeiro_mes_atual - timedelta(days=1)
        inicio = date(ultimo_mes_anterior.year, ultimo_mes_anterior.month, 1)
        return inicio, ultimo_mes_anterior

    if periodo == "ultimos_3_meses":
        return hoje - timedelta(days=90), hoje

    if periodo == "ultimos_6_meses":
        return hoje - timedelta(days=180), hoje

    if periodo == "ano_atual":
        return date(hoje.year, 1, 1), hoje

    if periodo == "tudo":
        return DATA_PISO, hoje

    # "mes_atual" e fallback seguro para qualquer valor desconhecido
    return date(hoje.year, hoje.month, 1), hoje
