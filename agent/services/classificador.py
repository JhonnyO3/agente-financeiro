from __future__ import annotations

from datetime import date
from typing import Any

from agent.agents_llm import criar_llm
from agent.config import settings
from agent.domain.intencao import (
    Acao,
    IntencaoClassificacao,
    Intencao,
    ParamsCadastrar,
    ParamsComplementar,
    ParamsExcluir,
    ParamsListar,
    ParamsSelecionar,
    ParamsVazio,
    _ACAO_PARA_PARAMS,
)
import logging

from agent.services.prompts import montar_prompt

logger = logging.getLogger(__name__)

_ACOES_REQUEREM_PENDENCIA = {"confirmar", "cancelar", "selecionar"}
_ACOES_SEM_PARAMS = {"conversar", "confirmar", "cancelar", "desconhecida"}


class Classificador:
    async def classificar(
        self,
        mensagem: str,
        historico: list[str],
        estado_pendente: str,
    ) -> Intencao:
        ctx = {
            "mensagem": mensagem,
            "historico_recente": "\n".join(historico) if historico else "",
            "estado_pendente": estado_pendente,
            "user_name": settings.RESPONSAVEL_PADRAO,
            "data_atual": date.today().strftime("%d/%m/%Y"),
        }

        # Passo 1 — classificar apenas a ação (schema simples, sem risco de flattening)
        prompt = montar_prompt("classificador", ctx)
        llm = criar_llm()
        chain = llm.with_structured_output(IntencaoClassificacao, method="function_calling")
        logger.info("classificador llm:classificar iniciando mensagem=%r estado_pendente=%r", mensagem[:80], estado_pendente)
        try:
            clf: IntencaoClassificacao = await chain.ainvoke(prompt)
        except Exception:
            logger.exception("classificador llm:classificar erro — retornando desconhecida")
            return Intencao(acao="desconhecida", parametros=ParamsVazio(), confianca=0.0)

        acao: Acao = clf.acao
        confianca: float = clf.confianca
        logger.info("classificador llm:classificar acao=%s confianca=%.2f", acao, confianca)

        if confianca < settings.CONFIANCA_MINIMA:
            logger.info("classificador confianca abaixo do minimo (%.2f < %.2f) — desconhecida", confianca, settings.CONFIANCA_MINIMA)
            return Intencao(acao="desconhecida", parametros=ParamsVazio(), confianca=confianca)

        if estado_pendente == "nenhuma" and acao in _ACOES_REQUEREM_PENDENCIA:
            logger.info("classificador acao=%s requer pendencia mas nao ha — desconhecida", acao)
            return Intencao(acao="desconhecida", parametros=ParamsVazio(), confianca=confianca)

        # Passo 2 — extrair parâmetros específicos da ação (schema focado por ação)
        logger.info("classificador llm:extrair_params acao=%s", acao)
        parametros = await self._extrair_params(acao, mensagem, ctx)
        logger.info("classificador llm:extrair_params concluido acao=%s params_type=%s", acao, type(parametros).__name__)

        return Intencao(acao=acao, parametros=parametros, confianca=confianca)

    async def _extrair_params(self, acao: str, mensagem: str, ctx: dict) -> Any:
        # cadastrar: extração é responsabilidade do Extrator downstream
        if acao == "cadastrar":
            return ParamsCadastrar(itens=[])

        # ações sem parâmetros estruturados
        if acao in _ACOES_SEM_PARAMS:
            return ParamsVazio()

        params_cls = _ACAO_PARA_PARAMS.get(acao)
        if params_cls is None or params_cls is ParamsVazio:
            return ParamsVazio()

        # Extração com schema simples e focado (sem nesting — sem flattening)
        extraction_prompt = [
            (
                "system",
                f"Extraia os parâmetros da mensagem para a ação '{acao}'. "
                f"Data atual: {ctx['data_atual']}. Usuário: {ctx['user_name']}. "
                "Retorne null para campos não mencionados.",
            ),
            ("human", mensagem),
        ]

        llm = criar_llm()
        try:
            chain = llm.with_structured_output(params_cls, method="function_calling")
            return await chain.ainvoke(extraction_prompt)
        except Exception:
            try:
                return params_cls()
            except Exception:
                return ParamsVazio()
