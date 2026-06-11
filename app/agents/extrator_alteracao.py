from datetime import date
from decimal import Decimal
from pydantic import BaseModel, field_validator
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.base import coagir_data, criar_llm


class ExtracaoAlteracaoResult(BaseModel):
    novo_valor: Decimal | None = None
    nova_descricao: str | None = None
    nova_categoria: str | None = None
    nova_data: date | None = None

    _normaliza_data = field_validator("nova_data", mode="before")(coagir_data)


class ExtratorAlteracao:
    def __init__(self):
        self._chain = criar_llm().with_structured_output(ExtracaoAlteracaoResult)

    async def extrair(self, mensagem: str, data_atual: date) -> ExtracaoAlteracaoResult:
        system = (
            "Extraia apenas os campos que o usuário deseja modificar em uma transação financeira. "
            "Campos não mencionados devem ser None. "
            f"Data atual: {data_atual.strftime('%d/%m/%Y')}."
        )
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=mensagem),
        ]
        return await self._chain.ainvoke(messages)
