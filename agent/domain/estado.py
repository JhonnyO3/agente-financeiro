from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Mensagem(BaseModel):
    papel: str
    texto: str
    em: datetime


class OpcaoPendente(BaseModel):
    numero: int
    rotulo: str
    ref: dict[str, Any]


class EstadoConversa(BaseModel):
    usuario_id: int
    acao_pendente: str | None = None
    payload_pendente: dict[str, Any] | None = None
    campos_faltantes: list[str] = Field(default_factory=list)
    opcoes: list[OpcaoPendente] | None = None
    historico: list[Mensagem] = Field(default_factory=list)
    expira_em: datetime | None = None
    historico_expira_em: datetime | None = None
