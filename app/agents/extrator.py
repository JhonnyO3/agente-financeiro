from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.base import carregar_prompt, criar_llm


class ExtracaoResult(BaseModel):
    tipo: Literal["GASTO", "INVESTIMENTO"]
    valor_total: Decimal
    valor_por_parcela: Decimal | None
    parcela_total: int = 1
    descricao: str | None
    data_referencia: date
    menciona_cartao: bool


class Extrator:
    def __init__(self):
        self._chain = criar_llm().with_structured_output(ExtracaoResult)
        self._prompt = carregar_prompt("sistema.md")

    async def extrair(self, mensagem: str, data_atual: date) -> ExtracaoResult:
        messages = [
            SystemMessage(content=self._prompt),
            HumanMessage(content=f"Data atual: {data_atual.strftime('%d/%m/%Y')}\n\n{mensagem}"),
        ]
        return await self._chain.ainvoke(messages)
