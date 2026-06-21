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
from agent.services.prompts import montar_prompt

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
        try:
            clf: IntencaoClassificacao = await chain.ainvoke(prompt)
        except Exception:
            return Intencao(acao="desconhecida", parametros=ParamsVazio(), confianca=0.0)

        acao: Acao = clf.acao
        confianca: float = clf.confianca

        if confianca < settings.CONFIANCA_MINIMA:
            return Intencao(acao="desconhecida", parametros=ParamsVazio(), confianca=confianca)

        if estado_pendente == "nenhuma" and acao in _ACOES_REQUEREM_PENDENCIA:
            return Intencao(acao="desconhecida", parametros=ParamsVazio(), confianca=confianca)

        # Passo 2 — extrair parâmetros específicos da ação (schema focado por ação)
        parametros = await self._extrair_params(acao, mensagem, ctx)

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
