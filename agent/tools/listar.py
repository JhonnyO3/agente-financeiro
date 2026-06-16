"""ToolListar — agregação determinística (zero LLM) para listar transações por período."""

from decimal import Decimal
from typing import Any

from agent.domain.intencao import ParamsListar
from agent.domain.resultado import ResultadoTool
from agent.services.parser_periodo import parsear_periodo
from agent.services.relogio import Relogio


class ToolListar:
    def __init__(self, repo: Any, relogio: Relogio, usuario_id: int) -> None:
        self._repo = repo
        self._relogio = relogio
        self._usuario_id = usuario_id

    async def executar(self, params: ParamsListar, contexto: dict) -> ResultadoTool:
        inicio, fim, periodo_label = parsear_periodo(params.periodo, self._relogio)

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
