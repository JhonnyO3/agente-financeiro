from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.base import carregar_prompt, criar_llm


class IntencaoResult(BaseModel):
    intencao: Literal["CADASTRAR", "ALTERAR", "EXCLUIR", "CONSULTAR", "FORA_DE_ESCOPO"]
    confianca: Literal["alta", "media", "baixa"]


class Classificador:
    def __init__(self):
        self._chain = criar_llm().with_structured_output(IntencaoResult)
        self._prompt = carregar_prompt("intencao.md")

    async def classificar(self, mensagem: str) -> IntencaoResult:
        messages = [
            SystemMessage(content=self._prompt),
            HumanMessage(content=mensagem),
        ]
        return await self._chain.ainvoke(messages)
