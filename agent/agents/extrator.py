from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, field_validator
from langchain_core.messages import SystemMessage, HumanMessage
from agent.agents.base import carregar_prompt, coagir_data, criar_llm


class ExtracaoResult(BaseModel):
    tipo: Literal["GASTO", "INVESTIMENTO", "RECEITA"]
    valor_total: Decimal
    valor_por_parcela: Decimal | None
    parcela_total: int = 1
    parcela_atual: int = 1
    descricao: str | None
    detalhes: str | None = None
    data_referencia: date
    menciona_cartao: bool
    forma_pagamento: Literal["CARTAO_CREDITO", "CARTAO_DEBITO", "PIX", "BOLETO"] = "PIX"
    responsavel: str = "Jhonatas"

    _normaliza_data = field_validator("data_referencia", mode="before")(coagir_data)


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
