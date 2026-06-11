from datetime import date
from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from agent.agents.base import criar_llm


class ExclusaoLoteResult(BaseModel):
    periodo: Literal["mes", "ano", "semana", "tudo"]
    mes: int | None = None
    ano: int | None = None
    categoria: str | None = None


class ExtratorExclusaoLote:
    def __init__(self):
        self._chain = criar_llm().with_structured_output(ExclusaoLoteResult)

    async def extrair(self, mensagem: str, data_atual: date) -> ExclusaoLoteResult:
        system = (
            f"Data atual: {data_atual.strftime('%d/%m/%Y')}. "
            "Extraia os filtros de uma solicitação de exclusão em lote de transações financeiras. "
            "periodo: 'mes' (mês específico ou atual), 'ano' (ano específico ou atual), 'semana' (semana atual), 'tudo' (sem filtro de período). "
            "mes: número do mês (1-12) se mencionado, senão None. "
            "ano: ano com 4 dígitos se mencionado, senão None. "
            "categoria: uma de ALIMENTACAO, TRANSPORTE, LAZER, INVESTIMENTO, GASTOS_FIXOS, COMPRAS se mencionada, senão None. "
            "Quando o usuário diz 'esse mês' ou 'do mês', use o mês e ano atuais. "
            "Quando diz 'mês passado', use o mês anterior. "
            "Quando diz 'esse ano', use o ano atual. "
            "Quando diz 'tudo' ou 'todos' sem período, use 'tudo'."
        )
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=mensagem),
        ]
        return await self._chain.ainvoke(messages)
