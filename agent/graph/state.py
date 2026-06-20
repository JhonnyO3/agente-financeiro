from __future__ import annotations

from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    usuario_id: int
    numero: str
    intencao: dict | None
    resultado: dict | None
    resposta: str | None
    acao_pendente: str | None    # "cadastrar" | "atualizar" | "excluir"
    fase_pendente: str | None    # "aguardando_confirmacao" | "aguardando_complemento" | ...
    payload_pendente: dict | None
    campos_faltantes: list[str]
    opcoes: list[dict] | None
    expira_em: str | None        # ISO 8601 UTC
