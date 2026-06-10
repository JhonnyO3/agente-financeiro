import enum


class TipoEnum(str, enum.Enum):
    GASTO = "GASTO"
    INVESTIMENTO = "INVESTIMENTO"
    RECEITA = "RECEITA"


class CategoriaEnum(str, enum.Enum):
    ALIMENTACAO = "ALIMENTACAO"
    TRANSPORTE = "TRANSPORTE"
    LAZER = "LAZER"
    EDUCACAO = "EDUCACAO"
    GASTOS_FIXOS = "GASTOS_FIXOS"
    COMPRAS = "COMPRAS"
    GASTOS_PONTUAIS = "GASTOS_PONTUAIS"
    INVESTIMENTO = "INVESTIMENTO"
    RECEITA = "RECEITA"


class StatusEnum(str, enum.Enum):
    PAGO = "PAGO"
    PENDENTE = "PENDENTE"


class FormaPagamentoEnum(str, enum.Enum):
    CARTAO_CREDITO = "CARTAO_CREDITO"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    PIX = "PIX"
    BOLETO = "BOLETO"
