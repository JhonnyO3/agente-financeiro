import enum


class TipoEnum(str, enum.Enum):
    GASTO = "GASTO"
    INVESTIMENTO = "INVESTIMENTO"


class CategoriaEnum(str, enum.Enum):
    ALIMENTACAO = "ALIMENTACAO"
    TRANSPORTE = "TRANSPORTE"
    LAZER = "LAZER"
    INVESTIMENTO = "INVESTIMENTO"
    GASTOS_FIXOS = "GASTOS_FIXOS"
    COMPRAS = "COMPRAS"
