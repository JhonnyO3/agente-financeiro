from pydantic import BaseModel, field_validator


def _validar_dia(valor: int | None) -> int | None:
    if valor is None:
        return None
    if valor < 1 or valor > 31:
        raise ValueError("dia deve estar entre 1 e 31")
    return valor


class CartaoCreate(BaseModel):
    model_config = {"extra": "ignore"}

    apelido: str
    dia_fechamento: int | None = None
    dia_vencimento: int | None = None
    cor: str | None = None
    ativo: bool = True

    @field_validator("apelido")
    @classmethod
    def _apelido_nao_vazio(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("apelido obrigatorio")
        return valor.strip()

    @field_validator("dia_fechamento", "dia_vencimento")
    @classmethod
    def _dia_valido(cls, valor: int | None) -> int | None:
        return _validar_dia(valor)


class CartaoUpdate(BaseModel):
    model_config = {"extra": "ignore"}

    apelido: str | None = None
    dia_fechamento: int | None = None
    dia_vencimento: int | None = None
    cor: str | None = None
    ativo: bool | None = None

    @field_validator("apelido")
    @classmethod
    def _apelido_nao_vazio(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        if not valor.strip():
            raise ValueError("apelido obrigatorio")
        return valor.strip()

    @field_validator("dia_fechamento", "dia_vencimento")
    @classmethod
    def _dia_valido(cls, valor: int | None) -> int | None:
        return _validar_dia(valor)


class CartaoResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    apelido: str
    dia_fechamento: int | None
    dia_vencimento: int | None
    cor: str | None
    ativo: bool
