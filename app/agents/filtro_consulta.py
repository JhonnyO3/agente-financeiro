from datetime import date
from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.base import criar_llm


class FiltroConsultaResult(BaseModel):
    tipo_consulta: Literal["mensal", "semanal", "geral", "grupo_parcela", "dinamico"]
    mes: int | None = None
    ano: int | None = None
    categoria: str | None = None
    descricao_grupo: str | None = None
    periodo_inicio: date | None = None
    periodo_fim: date | None = None


class FiltroConsulta:
    def __init__(self):
        self._chain = criar_llm().with_structured_output(FiltroConsultaResult)

    async def extrair(self, mensagem: str, data_atual: date) -> FiltroConsultaResult:
        system = (
            "Extraia os filtros de consulta financeira da mensagem do usuário. "
            "tipo_consulta: 'mensal' para mês específico, 'semanal' para semana, "
            "'geral' para tudo, 'grupo_parcela' para grupo de parcelas, 'dinamico' para período livre. "
            f"Data atual: {data_atual.strftime('%d/%m/%Y')}."
        )
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=mensagem),
        ]
        return await self._chain.ainvoke(messages)
