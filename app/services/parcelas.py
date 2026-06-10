"""Funções puras de datas e status de parcelas. Sem dependências de LLM ou DB."""

import calendar
from datetime import date

from app.models.enums import FormaPagamentoEnum, StatusEnum

_FORMAS_A_VISTA = {FormaPagamentoEnum.PIX, FormaPagamentoEnum.CARTAO_DEBITO}


def adicionar_meses(data: date, meses: int) -> date:
    """Soma/subtrai meses preservando o dia; clampa para o último dia do mês
    quando o dia não existe (31/01 + 1 → 28/02 ou 29 em bissexto)."""
    total_meses = (data.year * 12 + data.month - 1) + meses
    ano, mes = divmod(total_meses, 12)
    mes += 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(data.day, ultimo_dia))


def status_por_data(data: date, hoje: date | None = None) -> StatusEnum:
    """data < hoje → PAGO; senão PENDENTE."""
    if hoje is None:
        hoje = date.today()
    return StatusEnum.PAGO if data < hoje else StatusEnum.PENDENTE


def data_status_por_forma(
    data: date, forma_pagamento: FormaPagamentoEnum
) -> tuple[date, StatusEnum]:
    """À vista (PIX/CARTAO_DEBITO) → data real e PAGO; a prazo
    (CARTAO_CREDITO/BOLETO) → data deslocada para a fatura (mês seguinte,
    dia preservado) e PENDENTE."""
    if forma_pagamento in _FORMAS_A_VISTA:
        return data, StatusEnum.PAGO
    return adicionar_meses(data, 1), StatusEnum.PENDENTE


def datas_do_grupo(
    data_parcela_atual: date, parcela_atual: int, parcela_total: int
) -> list[date]:
    """Retorna as N datas do grupo (índice 0 = parcela 1), derivadas da data da
    parcela atual via adicionar_meses (anteriores retrocedem, seguintes avançam)."""
    return [
        adicionar_meses(data_parcela_atual, i + 1 - parcela_atual)
        for i in range(parcela_total)
    ]
