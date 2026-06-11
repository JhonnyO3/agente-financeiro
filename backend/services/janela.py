from datetime import date


def janela_meses(hoje: date) -> list[date]:
    base = hoje.year * 12 + hoje.month - 1 - 6
    return [date((base + i) // 12, (base + i) % 12 + 1, 1) for i in range(13)]


def ultimo_dia(mes: date) -> date:
    proximo = date(mes.year + (mes.month // 12), mes.month % 12 + 1, 1)
    return date.fromordinal(proximo.toordinal() - 1)
