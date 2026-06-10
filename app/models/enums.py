import enum


class TipoEnum(str, enum.Enum):
    GASTO = "GASTO"
    INVESTIMENTO = "INVESTIMENTO"
    RECEITA = "RECEITA"


class CategoriaEnum(str, enum.Enum):
    ALIMENTACAO = "ALIMENTACAO"
    TRANSPORTE = "TRANSPORTE"
    LAZER = "LAZER"
    INVESTIMENTO = "INVESTIMENTO"
    GASTOS_FIXOS = "GASTOS_FIXOS"
    COMPRAS = "COMPRAS"
    GASTOS_PONTUAIS = "GASTOS_PONTUAIS"
    OUTROS = "OUTROS"
    RECEITA = "RECEITA"
    PARCELAMENTOS = "PARCELAMENTOS"


class StatusEnum(str, enum.Enum):
    PAGO = "PAGO"
    PENDENTE = "PENDENTE"


class FormaPagamentoEnum(str, enum.Enum):
    PIX = "PIX"
    CARTAO = "CARTAO"
    OUTRO = "OUTRO"
