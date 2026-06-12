"""ToolListar — agregação determinística (zero LLM) para listar transações por período."""

import calendar
from datetime import date
from decimal import Decimal
from typing import Any

from agent.domain.intencao import ParamsListar
from agent.domain.resultado import ResultadoTool
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


def _primeiro_e_ultimo_dia(ano: int, mes: int) -> tuple[date, date]:
    ultimo = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, 1), date(ano, mes, ultimo)


def _resolver_periodo(periodo: str | None, relogio: Relogio) -> tuple[date, date, str]:
    """Resolve o período a partir do parâmetro, retornando (inicio, fim, label)."""
    hoje = relogio.hoje()

    if periodo is None or periodo == "mes_atual":
        inicio, fim = _primeiro_e_ultimo_dia(hoje.year, hoje.month)
        label = f"{_MESES_LABEL[hoje.month]}/{hoje.year}"
        return inicio, fim, label

    # Formato "YYYY-MM"
    if len(periodo) == 7 and periodo[4] == "-":
        try:
            ano, mes = int(periodo[:4]), int(periodo[5:])
            inicio, fim = _primeiro_e_ultimo_dia(ano, mes)
            label = f"{_MESES_LABEL[mes]}/{ano}"
            return inicio, fim, label
        except ValueError:
            pass

    # Nome de mês em português
    nome = periodo.strip().lower()
    if nome in _MESES_PT:
        mes = _MESES_PT[nome]
        ano = hoje.year
        inicio, fim = _primeiro_e_ultimo_dia(ano, mes)
        label = f"{_MESES_LABEL[mes]}/{ano}"
        return inicio, fim, label

    # Fallback: mês atual
    inicio, fim = _primeiro_e_ultimo_dia(hoje.year, hoje.month)
    label = f"{_MESES_LABEL[hoje.month]}/{hoje.year}"
    return inicio, fim, label


class ToolListar:
    def __init__(self, repo: Any, relogio: Relogio, usuario_id: int) -> None:
        self._repo = repo
        self._relogio = relogio
        self._usuario_id = usuario_id

    async def executar(self, params: ParamsListar, contexto: dict) -> ResultadoTool:
        inicio, fim, periodo_label = _resolver_periodo(params.periodo, self._relogio)

        transacoes = await self._repo.listar_por_periodo(inicio, fim)

        # Aplicar filtro de categoria localmente se informado
        if params.categoria:
            transacoes = [t for t in transacoes if t.categoria == params.categoria]

        # Aplicar filtro de status localmente se informado
        if params.status:
            transacoes = [t for t in transacoes if t.status == params.status]

        # Aplicar filtro de responsável localmente se informado
        if params.responsavel:
            transacoes = [
                t
                for t in transacoes
                if getattr(t, "responsavel", None) == params.responsavel
            ]

        if not transacoes:
            return ResultadoTool(
                acao="listar",
                status="vazio",
                dados={"periodo_label": periodo_label},
            )

        # Separar parcelados (parcela_total > 1) do restante
        avista = [t for t in transacoes if t.parcela_total <= 1]
        parcelados = [t for t in transacoes if t.parcela_total > 1]

        # Agrupar à-vista por categoria
        grupos_por_cat: dict[str, list] = {}
        for t in avista:
            grupos_por_cat.setdefault(t.categoria, []).append(t)

        grupos: list[dict] = []
        for titulo, itens in grupos_por_cat.items():
            subtotal = sum((t.valor for t in itens), Decimal("0"))
            grupos.append(
                {
                    "titulo": titulo,
                    "itens": [_item(t) for t in itens],
                    "subtotal": subtotal,
                }
            )

        # Seção PARCELAMENTOS
        if parcelados:
            subtotal_p = sum((t.valor for t in parcelados), Decimal("0"))
            grupos.append(
                {
                    "titulo": "PARCELAMENTOS",
                    "itens": [_item(t) for t in parcelados],
                    "subtotal": subtotal_p,
                }
            )

        # Totais
        total = sum((t.valor for t in transacoes), Decimal("0"))
        pendente = sum(
            (t.valor for t in transacoes if t.status == "PENDENTE"), Decimal("0")
        )
        pago = sum(
            (t.valor for t in transacoes if t.status == "PAGO"), Decimal("0")
        )

        return ResultadoTool(
            acao="listar",
            status="concluido",
            dados={
                "periodo_label": periodo_label,
                "grupos": grupos,
                "total": total,
                "pendente": pendente,
                "pago": pago,
            },
        )


def _item(t: Any) -> dict:
    return {
        "descricao": t.descricao,
        "valor": t.valor,
        "data": t.data,
        "status": t.status,
        "parcela_numero": t.parcela_numero,
        "parcela_total": t.parcela_total,
    }
