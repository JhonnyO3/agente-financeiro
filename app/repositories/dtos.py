from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.models.enums import CategoriaEnum, TipoEnum


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


@dataclass
class TransacaoUpdate:
    tipo: TipoEnum | None = None
    valor: Decimal | None = None
    descricao: str | None = None
    categoria: CategoriaEnum | None = None
    data: date | None = None


@dataclass
class AgregadoCategoria:
    categoria: CategoriaEnum
    total: Decimal
    quantidade: int
