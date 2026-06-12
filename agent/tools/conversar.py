from datetime import date
from typing import Any

from langchain_openai import ChatOpenAI

from agent.config import settings
from agent.domain.resultado import ResultadoTool
from agent.services.prompts import montar_prompt


def criar_llm(modelo: str, temperatura: float = 0.3) -> Any:
    return ChatOpenAI(model=modelo, temperature=temperatura)


class ToolConversar:
    def __init__(self, repository: Any = None) -> None:
        self._repository = repository

    async def executar(self, mensagem: str, historico: list) -> ResultadoTool:
        ctx = {
            "mensagem": mensagem,
            "historico_recente": historico,
            "data_atual": date.today().isoformat(),
            "user_name": settings.RESPONSAVEL_PADRAO,
            "estado_pendente": "",
        }

        prompt = montar_prompt("conversar", ctx)
        llm = criar_llm(settings.LLM_MODELO_CONVERSAR)
        resposta = await llm.ainvoke(prompt)

        return ResultadoTool(
            acao="conversar",
            status="concluido",
            dados={"resposta": resposta.content},
        )
