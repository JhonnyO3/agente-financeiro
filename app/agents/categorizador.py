from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.base import carregar_prompt, criar_llm


class CategorizacaoResult(BaseModel):
    categoria: Literal["ALIMENTACAO", "TRANSPORTE", "LAZER", "INVESTIMENTO", "GASTOS_FIXOS", "COMPRAS"]


class Categorizador:
    def __init__(self):
        self._chain = criar_llm().with_structured_output(CategorizacaoResult)
        self._prompt = carregar_prompt("categorizacao.md")

    async def categorizar(self, tipo: str, descricao: str | None, valor: float) -> CategorizacaoResult:
        if tipo == "INVESTIMENTO":
            return CategorizacaoResult(categoria="INVESTIMENTO")
        messages = [
            SystemMessage(content=self._prompt),
            HumanMessage(content=f"tipo: {tipo}, descricao: {descricao}, valor: {valor}"),
        ]
        return await self._chain.ainvoke(messages)
