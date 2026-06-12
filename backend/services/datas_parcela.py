"""Funções puras de datas e status de parcelas (backend).

Duplicadas de agent/services/parcelas.py — o backend não importa de `agent`.
Dependem apenas de datetime/calendar e backend.models.enums.
"""

import calendar
from datetime import date

from backend.models.enums import StatusEnum


def adicionar_meses(data: date, meses: int) -> date:
    """Soma/subtrai meses preservando o dia; clampa para o último dia do mês
    quando o dia não existe (31/01 + 1 → 28/02 ou 29 em bissexto)."""
    total_meses = (data.year * 12 + data.month - 1) + meses
    ano, mes = divmod(total_meses, 12)
    mes += 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(data.day, ultimo_dia))


def status_por_data(data: date, hoje: date | None = None) -> StatusEnum:
    """data < hoje → PAGO; senão PENDENTE. hoje default date.today()."""
    if hoje is None:
        hoje = date.today()
    return StatusEnum.PAGO if data < hoje else StatusEnum.PENDENTE


def datas_do_grupo(
    data_parcela_atual: date, parcela_atual: int, parcela_total: int
) -> list[date]:
    """Retorna parcela_total datas (índice 0 = parcela 1), ancorando a parcela
    atual em data_parcela_atual; anteriores retrocedem e seguintes avançam.

    datas[i] = adicionar_meses(data_parcela_atual, i + 1 - parcela_atual)
    """
    return [
        adicionar_meses(data_parcela_atual, i + 1 - parcela_atual)
        for i in range(parcela_total)
    ]
