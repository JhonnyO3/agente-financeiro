from pydantic import BaseModel

CATEGORIAS_GASTO = (
    "ALIMENTACAO",
    "TRANSPORTE",
    "LAZER",
    "EDUCACAO",
    "GASTOS_FIXOS",
    "COMPRAS",
    "GASTOS_PONTUAIS",
)


class EvolucaoMes(BaseModel):
    mes: str
    gastos: str
    investimentos: str
    receitas: str


class ProjecaoMes(BaseModel):
    mes: str
    gastos: str
    receitas: str
    investimentos: str
    saldo: str
    qtd_parcelas: int
