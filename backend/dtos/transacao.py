from typing import Any

from pydantic import BaseModel


class TransacaoCreateRequest(BaseModel):
    data: Any | None = None
    valor: Any | None = None
    tipo: Any | None = None
    categoria: Any | None = None
    descricao: Any | None = None
    status: Any | None = None
    forma_pagamento: Any | None = None
    responsavel: Any | None = None
    detalhes: Any | None = None


class TransacaoUpdateRequest(BaseModel):
    model_config = {"extra": "ignore"}

    data: Any | None = None
    valor: Any | None = None
    descricao: Any | None = None
    categoria: Any | None = None
    status: Any | None = None
    forma_pagamento: Any | None = None
    responsavel: Any | None = None
    detalhes: Any | None = None
