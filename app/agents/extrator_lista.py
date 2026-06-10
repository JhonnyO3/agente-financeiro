from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.base import criar_llm


class ItemLista(BaseModel):
    descricao: str
    valor: Decimal
    parcela_numero: int = 1
    parcela_total: int = 1
    data: date
    tipo: Literal["GASTO", "INVESTIMENTO"] = "GASTO"
    categoria: Literal["ALIMENTACAO", "TRANSPORTE", "LAZER", "INVESTIMENTO", "GASTOS_FIXOS", "COMPRAS", "GASTOS_PONTUAIS", "OUTROS"] = "OUTROS"


class ExtracaoListaResult(BaseModel):
    itens: list[ItemLista]


class ExtratorLista:
    def __init__(self):
        self._chain = criar_llm().with_structured_output(ExtracaoListaResult)

    async def extrair(self, mensagem: str, data_atual: date) -> ExtracaoListaResult:
        system = (
            f"Data atual: {data_atual.strftime('%d/%m/%Y')}. "
            "Extraia uma lista de transações financeiras a partir da mensagem do usuário. "
            "Para cada item extraia: descricao, valor (o valor da parcela atual), "
            "parcela_numero (número desta parcela, padrão 1), "
            "parcela_total (total de parcelas, padrão 1), "
            "data (data de vencimento; se não informada use a data atual), "
            "tipo (GASTO ou INVESTIMENTO), "
            "categoria (ALIMENTACAO, TRANSPORTE, LAZER, INVESTIMENTO, GASTOS_FIXOS, COMPRAS). "
            "Exemplos de interpretação: "
            "'1 de 12 de 592' → parcela_numero=1, parcela_total=12, valor=592/12≈49.33. "
            "'parcela 8 de 12 x 167' → parcela_numero=8, parcela_total=12, valor=167. "
            "'2 de 5 x 200' → parcela_numero=2, parcela_total=5, valor=200. "
            "Quando a data de vencimento for mencionada (ex: 'vencendo dia 10/06'), use-a com o ano atual. "
            "Categorize com bom senso: uber/gasolina/estacionamento→TRANSPORTE, mercado/comida→ALIMENTACAO, "
            "assinaturas recorrentes (Netflix, Spotify, academia, LinkedIn)→GASTOS_FIXOS, "
            "roupas/eletrônicos/presentes→COMPRAS, investimentos→INVESTIMENTO, "
            "cursos pontuais/consertos/taxas eventuais→GASTOS_PONTUAIS, "
            "qualquer coisa que não se encaixa→OUTROS."
        )
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=mensagem),
        ]
        return await self._chain.ainvoke(messages)
