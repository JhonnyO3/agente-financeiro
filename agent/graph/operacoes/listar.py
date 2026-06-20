from __future__ import annotations

from typing import TYPE_CHECKING

from agent.graph.state import AgentState

if TYPE_CHECKING:
    from collections.abc import Callable
    from agent.services.relogio import Relogio
    from backend.repositories.transacao_repository import TransacaoRepository


def _limpar_pendencia() -> dict:
    return {
        "acao_pendente": None,
        "fase_pendente": None,
        "payload_pendente": None,
        "campos_faltantes": [],
        "opcoes": None,
        "expira_em": None,
    }


class Listar:
    def __init__(
        self,
        *,
        relogio: Relogio,
        repo_factory: Callable[[int], TransacaoRepository],
    ) -> None:
        self._relogio = relogio
        self._repo_factory = repo_factory

    async def executar(self, state: AgentState) -> dict:
        from agent.domain.intencao import ParamsListar
        from agent.tools.listar import ToolListar

        # Listar nunca tem fases — limpa pendência stale se houver
        updates: dict = _limpar_pendencia()

        intencao = state.get("intencao") or {}
        params_raw = intencao.get("parametros") or {}
        params = ParamsListar.model_validate(params_raw) if isinstance(params_raw, dict) else params_raw
        if not isinstance(params, ParamsListar):
            params = ParamsListar()

        usuario_id = state["usuario_id"]
        repo = self._repo_factory(usuario_id)
        tool = ToolListar(repo=repo, relogio=self._relogio, usuario_id=usuario_id)

        mensagem = state["messages"][-1].content if state.get("messages") else ""
        resultado = await tool.executar(params, {"mensagem": mensagem})

        updates["resultado"] = resultado.model_dump(mode="json")
        return updates
