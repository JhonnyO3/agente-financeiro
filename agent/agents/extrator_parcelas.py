from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from agent.agents.base import criar_llm


class ExtratorParcelasResult(BaseModel):
    parcela_total: int


class ExtratorParcelas:
    def __init__(self):
        self._chain = criar_llm().with_structured_output(ExtratorParcelasResult)

    async def extrair(self, mensagem: str) -> ExtratorParcelasResult:
        system = (
            "Extraia o número de parcelas da mensagem do usuário. "
            "'3 vezes' → 3, 'à vista' → 1, '6x' → 6. "
            "Retorne apenas o número inteiro."
        )
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=mensagem),
        ]
        return await self._chain.ainvoke(messages)
