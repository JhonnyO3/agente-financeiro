from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from agent.graph.state import AgentState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from agent.graph.operacao import Operacao
    from agent.integrations.evolution_client import EvolutionApiClient
    from agent.services.classificador import Classificador
    from agent.services.formatador import Formatador


def _resumir_pendencia(state: AgentState) -> str:
    acao = state.get("acao_pendente")
    if not acao:
        return "nenhuma"
    expira_em = state.get("expira_em")
    if expira_em:
        try:
            expira = datetime.fromisoformat(expira_em)
            if datetime.now(timezone.utc) > expira:
                return "nenhuma"
        except ValueError:
            return "nenhuma"
    fase = state.get("fase_pendente") or "pendente"
    return f"{acao} ({fase})"


def criar_no_classificar(
    classificador: Classificador,
) -> Callable[[AgentState], Awaitable[dict]]:
    async def no_classificar(state: AgentState) -> dict:
        mensagem = state["messages"][-1].content if state.get("messages") else ""
        msgs_prev = (state.get("messages") or [])[:-1]
        historico = [
            f"{m.type}: {m.content}"
            for m in msgs_prev[-2:]  # apenas as 2 últimas para contexto de pendência sem contaminar
        ]
        intencao = await classificador.classificar(
            mensagem=str(mensagem),
            historico=historico,
            estado_pendente=_resumir_pendencia(state),
        )
        return {"intencao": intencao.model_dump(mode="json")}

    return no_classificar


def criar_no_operacao(
    operacao: Operacao,
) -> Callable[[AgentState], Awaitable[dict]]:
    async def no_operacao(state: AgentState) -> dict:
        return await operacao.executar(state)

    return no_operacao


def criar_no_formatar(
    formatador: Formatador,
) -> Callable[[AgentState], Awaitable[dict]]:
    async def no_formatar(state: AgentState) -> dict:
        from agent.domain.resultado import ResultadoTool

        resultado_raw = state.get("resultado") or {}
        resultado = ResultadoTool.model_validate(resultado_raw)
        resposta = formatador.formatar(resultado)
        return {"resposta": resposta}

    return no_formatar


def criar_no_cancelar() -> Callable[[AgentState], Awaitable[dict]]:
    async def no_cancelar(state: AgentState) -> dict:
        return {
            "resultado": {"acao": "cancelar", "status": "concluido", "dados": {}},
            "acao_pendente": None,
            "fase_pendente": None,
            "payload_pendente": None,
            "campos_faltantes": [],
            "opcoes": None,
            "expira_em": None,
        }

    return no_cancelar


def criar_no_enviar(
    evolution: EvolutionApiClient,
) -> Callable[[AgentState], Awaitable[dict]]:
    async def no_enviar(state: AgentState) -> dict:
        numero = state["numero"]
        resposta = state.get("resposta") or ""
        await evolution.enviar_mensagem(numero, resposta)
        return {}

    return no_enviar
