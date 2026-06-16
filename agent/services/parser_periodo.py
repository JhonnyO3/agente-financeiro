import calendar
from datetime import date, timedelta

from agent.services.relogio import Relogio

_MESES_PT: dict[str, int] = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

_MESES_LABEL: dict[int, str] = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}


def _primeiro_e_ultimo(ano: int, mes: int) -> tuple[date, date]:
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, 1), date(ano, mes, ultimo_dia)


def _label_mes(ano: int, mes: int) -> str:
    return f"{_MESES_LABEL[mes]}/{ano}"


def parsear_periodo(periodo: str | None, relogio: Relogio) -> tuple[date, date, str]:
    """
    Resolve a string de período para (inicio, fim, label).
    NUNCA levanta exceção — fallback silencioso para o mês atual.
    """
    hoje = relogio.hoje()

    def _fallback() -> tuple[date, date, str]:
        inicio, fim = _primeiro_e_ultimo(hoje.year, hoje.month)
        return inicio, fim, _label_mes(hoje.year, hoje.month)

    if periodo is None:
        return _fallback()

    p = periodo.strip()

    if p == "hoje":
        return hoje, hoje, "hoje"

    if p == "ontem":
        ontem = hoje - timedelta(days=1)
        return ontem, ontem, "ontem"

    if p == "semana_atual":
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
        return inicio, fim, "semana atual"

    if p == "semana_passada":
        inicio_atual = hoje - timedelta(days=hoje.weekday())
        inicio = inicio_atual - timedelta(days=7)
        fim = inicio + timedelta(days=6)
        return inicio, fim, "semana passada"

    if p == "mes_atual":
        return _fallback()

    if p == "mes_passado":
        primeiro_do_mes_atual = date(hoje.year, hoje.month, 1)
        ultimo_mes_passado = primeiro_do_mes_atual - timedelta(days=1)
        inicio, fim = _primeiro_e_ultimo(
            ultimo_mes_passado.year, ultimo_mes_passado.month
        )
        return (
            inicio,
            fim,
            _label_mes(ultimo_mes_passado.year, ultimo_mes_passado.month),
        )

    # YYYY-MM-DD (length 10, position 4 and 7 are "-")
    if len(p) == 10 and p[4] == "-" and p[7] == "-":
        try:
            d = date.fromisoformat(p)
            return d, d, d.strftime("%d/%m/%Y")
        except ValueError:
            return _fallback()

    # YYYY-MM (length 7, position 4 is "-")
    if len(p) == 7 and p[4] == "-":
        try:
            ano = int(p[:4])
            mes = int(p[5:])
            if not (1 <= mes <= 12):
                return _fallback()
            inicio, fim = _primeiro_e_ultimo(ano, mes)
            return inicio, fim, _label_mes(ano, mes)
        except ValueError:
            return _fallback()

    # nome de mês PT (normalise to lower for lookup)
    p_lower = p.lower()
    if p_lower in _MESES_PT:
        mes = _MESES_PT[p_lower]
        inicio, fim = _primeiro_e_ultimo(hoje.year, mes)
        return inicio, fim, _label_mes(hoje.year, mes)

    return _fallback()
