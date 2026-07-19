from decimal import Decimal

from pydantic import BaseModel

from backend.models.enums import CategoriaEnum, FormaPagamentoEnum, TipoEnum

_CENTAVOS = Decimal("0.01")


class RecorrenciaCreate(BaseModel):
    descricao: str
    tipo: TipoEnum = TipoEnum.GASTO
    categoria: CategoriaEnum = CategoriaEnum.GASTOS_FIXOS
    valor: Decimal
    dia_vencimento: int | None = None
    forma_pagamento: FormaPagamentoEnum | None = None
    ativo: bool = True


class RecorrenciaUpdate(BaseModel):
    model_config = {"extra": "ignore"}

    descricao: str | None = None
    tipo: TipoEnum | None = None
    categoria: CategoriaEnum | None = None
    valor: Decimal | None = None
    dia_vencimento: int | None = None
    forma_pagamento: FormaPagamentoEnum | None = None
    ativo: bool | None = None


class RecorrenciaResponse(BaseModel):
    id: int
    usuario_id: int
    descricao: str
    tipo: str
    categoria: str
    valor: str
    dia_vencimento: int | None = None
    forma_pagamento: str | None = None
    ativo: bool
    criado_em: str | None = None
    encerrado_em: str | None = None

    @classmethod
    def de_modelo(cls, recorrencia) -> "RecorrenciaResponse":
        def _valor_str(campo) -> str:
            return getattr(campo, "value", campo)

        def _iso(campo) -> str | None:
            if campo is None:
                return None
            return campo.isoformat() if hasattr(campo, "isoformat") else str(campo)

        return cls(
            id=recorrencia.id,
            usuario_id=recorrencia.usuario_id,
            descricao=recorrencia.descricao,
            tipo=_valor_str(recorrencia.tipo),
            categoria=_valor_str(recorrencia.categoria),
            valor=str(Decimal(str(recorrencia.valor)).quantize(_CENTAVOS)),
            dia_vencimento=recorrencia.dia_vencimento,
            forma_pagamento=(
                _valor_str(recorrencia.forma_pagamento)
                if recorrencia.forma_pagamento is not None
                else None
            ),
            ativo=recorrencia.ativo,
            criado_em=_iso(recorrencia.criado_em),
            encerrado_em=_iso(recorrencia.encerrado_em),
        )
