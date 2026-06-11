from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from agent.agents.base import criar_llm


class ConfirmacaoResposta(BaseModel):
    tipo: Literal["sim", "nao", "parcela", "grupo"]


class ConfirmacaoChain:
    def __init__(self):
        self._chain = criar_llm(temperatura=0.0).with_structured_output(ConfirmacaoResposta)

    async def interpretar(
        self, mensagem: str, contexto: Literal["sim_nao", "escopo_parcela"]
    ) -> ConfirmacaoResposta:
        if contexto == "sim_nao":
            instrucao = "Interprete a resposta como 'sim' ou 'nao'."
        else:
            instrucao = "Interprete a resposta como 'parcela' (só esta parcela) ou 'grupo' (todas as parcelas)."
        messages = [
            SystemMessage(content=instrucao),
            HumanMessage(content=mensagem),
        ]
        return await self._chain.ainvoke(messages)
