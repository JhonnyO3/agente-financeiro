from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.models.enums import CategoriaEnum, FormaPagamentoEnum, StatusEnum, TipoEnum


@dataclass
class TransacaoCreate:
    tipo: TipoEnum
    valor: Decimal
    descricao: str | None
    categoria: CategoriaEnum
    data: date
    parcela_numero: int
    parcela_total: int
    grupo_parcela_id: UUID
    embedding: list[float]
    status: StatusEnum = StatusEnum.PENDENTE
    forma_pagamento: FormaPagamentoEnum = FormaPagamentoEnum.OUTRO
    responsavel: str = "Jhonatas"
    detalhes: str | None = None


@dataclass
class TransacaoUpdate:
    tipo: TipoEnum | None = None
    valor: Decimal | None = None
    descricao: str | None = None
    categoria: CategoriaEnum | None = None
    data: date | None = None
    status: StatusEnum | None = None
    forma_pagamento: FormaPagamentoEnum | None = None
    responsavel: str | None = None
    detalhes: str | None = None


@dataclass
class AgregadoCategoria:
    categoria: CategoriaEnum
    total: Decimal
    quantidade: int
