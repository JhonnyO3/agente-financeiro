"""
Tool Excluir — Task 10.
RAG 3 faixas: MATCH→aguardando_confirmacao ou aguardando_escopo (parcelado),
AMBIGUO→aguardando_selecao, PISO→nao_encontrado.
Modo lote (só periodo, sem referencia) → count + aguardando_confirmacao.
Nunca persiste.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from agent.domain.intencao import ParamsExcluir
from agent.domain.resultado import ResultadoTool
from agent.services.relogio import Relogio

if TYPE_CHECKING:
    from agent.services.rag import BuscaRAG

_MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


def _rotulo_parcela(data: Any) -> str:
    return f"{_MESES_PT[data.month]}/{str(data.year)[2:]}"


def _periodo_label(periodo: str) -> str:
    """'2026-05' → 'Mai/2026'."""
    try:
        ano, mes = periodo.split("-")
        return f"{_MESES_PT[int(mes)]}/{ano}"
    except Exception:
        return periodo


def _transacao_para_dict(t: Any) -> dict:
    return {
        "id": t.id,
        "descricao": t.descricao,
        "valor": t.valor,
        "data": t.data,
        "categoria": t.categoria,
        "forma_pagamento": t.forma_pagamento,
        "status": t.status,
        "parcela_numero": t.parcela_numero,
        "parcela_total": t.parcela_total,
        "grupo_parcela_id": t.grupo_parcela_id,
        "responsavel": t.responsavel,
        "detalhes": t.detalhes,
    }


class ToolExcluir:
    def __init__(self, rag: Any, repository: Any, relogio: Relogio) -> None:
        self._rag = rag
        self._repo = repository
        self._relogio = relogio

    async def executar(self, params: ParamsExcluir, usuario_id: int) -> ResultadoTool:
        # Modo lote: apenas periodo sem referencia
        if params.referencia is None and params.periodo:
            qtd = await self._repo.contar_por_periodo_e_categoria(
                periodo=params.periodo,
                categoria=params.categoria,
                usuario_id=usuario_id,
            )
            return ResultadoTool(
                acao="excluir",
                status="aguardando_confirmacao",
                dados={
                    "modo": "lote",
                    "qtd": qtd,
                    "periodo_label": _periodo_label(params.periodo),
                    "periodo": params.periodo,
                    "categoria": params.categoria,
                },
            )

        # Modo individual: busca RAG
        from agent.services.rag import Faixa

        busca = await self._rag.buscar(params.referencia, usuario_id)

        if busca.faixa == Faixa.PISO:
            return ResultadoTool(
                acao="excluir",
                status="nao_encontrado",
                dados={"referencia": params.referencia},
            )

        if busca.faixa == Faixa.AMBIGUO:
            opcoes = [
                {
                    "numero": i + 1,
                    "id": t.id,
                    "descricao": t.descricao,
                    "valor": t.valor,
                    "data": t.data,
                    "distancia": d,
                }
                for i, (t, d) in enumerate(busca.candidatos)
            ]
            return ResultadoTool(
                acao="excluir",
                status="aguardando_selecao",
                dados={"opcoes": opcoes, "modo": "individual"},
            )

        # MATCH
        transacao, _ = busca.candidatos[0]

        # Verifica parcelas futuras
        futuras: list[Any] = []
        if transacao.parcela_total and transacao.parcela_total > 1:
            futuras = await self._repo.buscar_parcelas_futuras_grupo(
                transacao.grupo_parcela_id, transacao.data
            )

        if futuras:
            parcelas_futuras = [_rotulo_parcela(f.data) for f in futuras]
            return ResultadoTool(
                acao="excluir",
                status="aguardando_escopo",
                dados={
                    "registro": _transacao_para_dict(transacao),
                    "parcelas_futuras": parcelas_futuras,
                },
            )

        return ResultadoTool(
            acao="excluir",
            status="aguardando_confirmacao",
            dados={"registro": _transacao_para_dict(transacao)},
        )
