from __future__ import annotations

from agent.graph.state import AgentState


def _limpar_pendencia() -> dict:
    return {
        "acao_pendente": None,
        "fase_pendente": None,
        "payload_pendente": None,
        "campos_faltantes": [],
        "opcoes": None,
        "expira_em": None,
    }


class Conversar:
    async def executar(self, state: AgentState) -> dict:
        from agent.tools.conversar import ToolConversar

        # Conversar nunca tem fases — limpa pendência stale se houver
        updates: dict = _limpar_pendencia()

        mensagem = state["messages"][-1].content if state.get("messages") else ""

        # Formata histórico anterior (exclui a mensagem atual — último item)
        historico = [
            f"{m.type}: {m.content}"
            for m in (state.get("messages") or [])[:-1]
        ]

        tool = ToolConversar()
        resultado = await tool.executar(mensagem, historico)

        updates["resultado"] = resultado.model_dump(mode="json")
        return updates
