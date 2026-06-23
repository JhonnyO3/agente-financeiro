from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from agent.graph.state import AgentState

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from agent.graph.operacao import Operacao
    from agent.integrations.evolution_client import EvolutionApiClient
    from agent.services.classificador import Classificador
    from agent.services.formatador import Formatador

logger = logging.getLogger(__name__)


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
        pendencia = _resumir_pendencia(state)
        logger.info("node:classificar numero=%s pendencia=%r mensagem=%r", state.get("numero"), pendencia, str(mensagem)[:80])
        intencao = await classificador.classificar(
            mensagem=str(mensagem),
            historico=historico,
            estado_pendente=pendencia,
        )
        logger.info("node:classificar resultado acao=%s confianca=%.2f numero=%s", intencao.acao, intencao.confianca, state.get("numero"))
        return {"intencao": intencao.model_dump(mode="json")}

    return no_classificar


def criar_no_operacao(
    operacao: Operacao,
) -> Callable[[AgentState], Awaitable[dict]]:
    async def no_operacao(state: AgentState) -> dict:
        intencao = state.get("intencao") or {}
        logger.info("node:operacao inicio numero=%s acao=%s", state.get("numero"), intencao.get("acao"))
        resultado = await operacao.executar(state)
        status = (resultado.get("resultado") or {}).get("status", "?")
        logger.info("node:operacao fim numero=%s acao=%s status=%s", state.get("numero"), intencao.get("acao"), status)
        return resultado

    return no_operacao


def criar_no_formatar(
    formatador: Formatador,
) -> Callable[[AgentState], Awaitable[dict]]:
    async def no_formatar(state: AgentState) -> dict:
        from agent.domain.resultado import ResultadoTool

        resultado_raw = state.get("resultado") or {}
        resultado = ResultadoTool.model_validate(resultado_raw)
        logger.info("node:formatar numero=%s acao=%s status=%s", state.get("numero"), resultado.acao, resultado.status)
        resposta = formatador.formatar(resultado)
        logger.info("node:formatar resposta numero=%s chars=%d", state.get("numero"), len(resposta))
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
        logger.info("node:enviar numero=%s chars=%d", numero, len(resposta))
        await evolution.enviar_mensagem(numero, resposta)
        logger.info("node:enviar entregue numero=%s", numero)
        return {}

    return no_enviar
