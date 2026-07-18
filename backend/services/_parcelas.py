import calendar
from datetime import date
from decimal import ROUND_DOWN, Decimal


def adicionar_meses(data: date, meses: int) -> date:
    total_meses = (data.year * 12 + data.month - 1) + meses
    ano, mes = divmod(total_meses, 12)
    mes += 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(data.day, ultimo_dia))


def valores_das_parcelas(valor_total: Decimal, parcela_total: int) -> list[Decimal]:
    base = (valor_total / parcela_total).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return [base] * (parcela_total - 1) + [valor_total - base * (parcela_total - 1)]
