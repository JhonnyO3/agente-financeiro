from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

from backend.models.enums import CategoriaEnum

_CATEGORIAS_VALIDAS = {c.value for c in CategoriaEnum}
_CEM = Decimal("100")


class PreferenciasBody(BaseModel):
    model_config = {"extra": "ignore"}

    renda_mensal: Decimal | None = None
    metas: dict[str, Decimal] = {}

    @field_validator("renda_mensal")
    @classmethod
    def _renda_nao_negativa(cls, valor: Decimal | None) -> Decimal | None:
        if valor is not None and valor < 0:
            raise ValueError("renda_mensal nao pode ser negativa")
        return valor

    @field_validator("metas")
    @classmethod
    def _metas_validas(cls, metas: dict[str, Decimal]) -> dict[str, Decimal]:
        for categoria, percentual in metas.items():
            if categoria not in _CATEGORIAS_VALIDAS:
                raise ValueError(f"categoria invalida: {categoria}")
            if percentual < 0 or percentual > _CEM:
                raise ValueError(
                    f"percentual de {categoria} deve estar entre 0 e 100"
                )
        return metas

    @model_validator(mode="after")
    def _soma_ate_cem(self) -> "PreferenciasBody":
        if sum(self.metas.values(), Decimal("0")) > _CEM:
            raise ValueError("a soma das metas nao pode passar de 100%")
        return self


class PreferenciasResponse(BaseModel):
    renda_mensal: str | None = None
    metas: dict[str, float]
    atualizado_em: str | None = None

    @classmethod
    def de_modelo(cls, preferencias) -> "PreferenciasResponse":
        renda = preferencias.renda_mensal
        renda_str = str(Decimal(str(renda)).quantize(Decimal("0.01"))) if renda is not None else None
        atualizado = preferencias.atualizado_em
        atualizado_iso = (
            atualizado.isoformat() if hasattr(atualizado, "isoformat") else str(atualizado)
        )
        return cls(
            renda_mensal=renda_str,
            metas={k: float(v) for k, v in (preferencias.metas or {}).items()},
            atualizado_em=atualizado_iso,
        )
