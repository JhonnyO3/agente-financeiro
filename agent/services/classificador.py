from datetime import date

from agent.agents_llm import criar_llm
from agent.config import settings
from agent.domain.intencao import Intencao, ParamsVazio
from agent.services.prompts import montar_prompt

_ACOES_REQUEREM_PENDENCIA = {"confirmar", "cancelar", "selecionar"}


class Classificador:
    async def classificar(
        self,
        mensagem: str,
        historico: list[str],
        estado_pendente: str,
    ) -> Intencao:
        historico_recente = "\n".join(historico) if historico else ""

        ctx = {
            "mensagem": mensagem,
            "historico_recente": historico_recente,
            "estado_pendente": estado_pendente,
            "user_name": settings.RESPONSAVEL_PADRAO,
            "data_atual": date.today().strftime("%d/%m/%Y"),
        }

        prompt = montar_prompt("classificador", ctx)

        llm = criar_llm()
        chain = llm.with_structured_output(Intencao, method="function_calling")
        intencao: Intencao = await chain.ainvoke(prompt)

        if intencao.confianca < settings.CONFIANCA_MINIMA:
            return Intencao(acao="desconhecida", parametros=ParamsVazio(), confianca=intencao.confianca)

        if estado_pendente == "nenhuma" and intencao.acao in _ACOES_REQUEREM_PENDENCIA:
            return Intencao(acao="desconhecida", parametros=ParamsVazio(), confianca=intencao.confianca)

        return intencao
