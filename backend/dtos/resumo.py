from pydantic import BaseModel


class ResumoResponse(BaseModel):
    gastos: str
    receitas: str
    investimentos: str
    saldo: str
    periodo: str


class CategoriaResponse(BaseModel):
    categoria: str
    total: str
    percentual: float
