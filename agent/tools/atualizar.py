"""
Tool Atualizar — Task 10.
RAG 3 faixas: MATCH→diff/aguardando_confirmacao, AMBIGUO→aguardando_selecao, PISO→nao_encontrado.
Propaga valor/data para parcelas futuras; status não propaga.
Nunca persiste (payload pendente).
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from agent.domain.intencao import ParamsAtualizar
from agent.domain.resultado import ResultadoTool
from agent.services.relogio import Relogio

if TYPE_CHECKING:
    from agent.services.rag import BuscaRAG

_MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}

_PROPAGA_CAMPOS = {"valor", "data"}


def _rotulo_parcela(data: Any) -> str:
    """Formata data como Mês/AA (ex: Jul/26)."""
    return f"{_MESES_PT[data.month]}/{str(data.year)[2:]}"


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


def _valor_antigo(transacao: Any, campo: str) -> str:
    val = getattr(transacao, campo)
    if hasattr(val, "value"):
        return val.value.upper() if hasattr(val.value, "upper") else str(val.value)
    if hasattr(val, "name"):
        return val.name.upper()
    return str(val)


class ToolAtualizar:
    def __init__(self, rag: Any, repository: Any, relogio: Relogio) -> None:
        self._rag = rag
        self._repo = repository
        self._relogio = relogio

    async def executar(self, params: ParamsAtualizar, usuario_id: int) -> ResultadoTool:
        from agent.services.rag import Faixa

        busca = await self._rag.buscar(params.referencia, usuario_id)

        if busca.faixa == Faixa.PISO:
            return ResultadoTool(
                acao="atualizar",
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
                acao="atualizar",
                status="aguardando_selecao",
                dados={"opcoes": opcoes},
            )

        # MATCH
        transacao, _ = busca.candidatos[0]
        campo = params.campo or ""
        novo_valor = params.novo_valor or ""

        antigo = _valor_antigo(transacao, campo) if campo else ""

        parcelas_afetadas: list[str] = []
        if campo in _PROPAGA_CAMPOS and transacao.parcela_total and transacao.parcela_total > 1:
            futuras = await self._repo.buscar_parcelas_futuras_grupo(
                transacao.grupo_parcela_id, transacao.data
            )
            parcelas_afetadas = [_rotulo_parcela(f.data) for f in futuras]

        diff = {"campo": campo, "antigo": antigo, "novo": novo_valor}

        dados: dict = {
            "registro": _transacao_para_dict(transacao),
            "diff": diff,
            "parcelas_afetadas": parcelas_afetadas,
        }

        return ResultadoTool(
            acao="atualizar",
            status="aguardando_confirmacao",
            dados=dados,
        )
