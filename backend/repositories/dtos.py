from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from backend.models.enums import (
    CategoriaEnum,
    FormaPagamentoEnum,
    RoleEnum,
    StatusEnum,
    TipoEnum,
)


@dataclass
class TransacaoCreate:
    usuario_id: int
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
    forma_pagamento: FormaPagamentoEnum = FormaPagamentoEnum.PIX
    recorrente: bool = False
    responsavel: str = "Jhonatas"
    detalhes: str | None = None
    cartao_id: int | None = None


@dataclass
class TransacaoUpdate:
    tipo: TipoEnum | None = None
    valor: Decimal | None = None
    descricao: str | None = None
    categoria: CategoriaEnum | None = None
    data: date | None = None
    status: StatusEnum | None = None
    forma_pagamento: FormaPagamentoEnum | None = None
    recorrente: bool | None = None
    responsavel: str | None = None
    detalhes: str | None = None
    cartao_id: int | None = None


@dataclass
class UsuarioCreate:
    nome: str
    username: str
    email: str
    senha_hash: str
    telefone: str | None = None
    role: RoleEnum = RoleEnum.USER
    ativo: bool = True


@dataclass
class UsuarioUpdate:
    nome: str | None = None
    username: str | None = None
    email: str | None = None
    senha_hash: str | None = None
    telefone: str | None = None
    role: RoleEnum | None = None
    ativo: bool | None = None


@dataclass
class AgregadoCategoria:
    categoria: CategoriaEnum
    total: Decimal
    quantidade: int
