from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # LangGraph gerencia append automaticamente via add_messages
    messages: Annotated[list[BaseMessage], add_messages]

    # Contexto da mensagem atual — preenchido pelo Consumer na entrada
    usuario_id: int
    numero: str

    # Output do nó classificar
    intencao: dict | None

    # Output do nó operação (cadastrar/listar/etc)
    resultado: dict | None

    # Output do nó formatar — consumido pelo nó enviar
    resposta: str | None

    # Estado pendente — persiste entre turnos via checkpointer
    acao_pendente: str | None    # "cadastrar" | "atualizar" | "excluir"
    fase_pendente: str | None    # "aguardando_confirmacao" | "aguardando_selecao"
                                 # | "aguardando_complemento" | "aguardando_escopo"
    payload_pendente: dict | None
    campos_faltantes: list[str]
    opcoes: list[dict] | None
    expira_em: str | None        # ISO 8601 UTC — TTL da pendência
