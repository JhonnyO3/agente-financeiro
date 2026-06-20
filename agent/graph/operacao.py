from __future__ import annotations

from typing import Protocol

from agent.graph.state import AgentState


class Operacao(Protocol):
    async def executar(self, state: AgentState) -> dict: ...
