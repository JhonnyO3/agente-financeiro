from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator

Acao = Literal[
    "cadastrar",
    "listar",
    "atualizar",
    "excluir",
    "conversar",
    "confirmar",
    "cancelar",
    "selecionar",
    "complementar",
    "desconhecida",
]


class ItemCadastro(BaseModel):
    descricao: str | None = None
    valor: Decimal | None = None
    forma_pagamento: (
        Literal["PIX", "CARTAO_CREDITO", "CARTAO_DEBITO", "BOLETO", "DINHEIRO"] | None
    ) = None
    parcela_atual: int | None = None
    total_parcelas: int | None = None
    dia_vencimento: int | None = None
    data: str | None = None
    tipo: Literal["GASTO", "INVESTIMENTO", "RECEITA"] | None = None


class ParamsCadastrar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itens: list[ItemCadastro]


class ParamsListar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    periodo: str | None = None
    categoria: str | None = None
    responsavel: str | None = None
    status: Literal["PAGO", "PENDENTE"] | None = None


class ParamsAtualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    referencia: str | None = None
    campo: (
        Literal["valor", "data", "status", "categoria", "descricao", "forma_pagamento"]
        | None
    ) = None
    novo_valor: str | None = None


class ParamsExcluir(BaseModel):
    model_config = ConfigDict(extra="forbid")

    referencia: str | None = None
    periodo: str | None = None
    categoria: str | None = None


class ParamsSelecionar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opcao: int


class ParamsComplementar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campo: str
    valor: str


class ParamsVazio(BaseModel):
    model_config = ConfigDict(extra="forbid")


ParametrosPorAcao = (
    ParamsCadastrar
    | ParamsListar
    | ParamsAtualizar
    | ParamsExcluir
    | ParamsSelecionar
    | ParamsComplementar
    | ParamsVazio
)

_ACAO_PARA_PARAMS: dict[str, type[BaseModel]] = {
    "cadastrar": ParamsCadastrar,
    "listar": ParamsListar,
    "atualizar": ParamsAtualizar,
    "excluir": ParamsExcluir,
    "conversar": ParamsVazio,
    "confirmar": ParamsVazio,
    "cancelar": ParamsVazio,
    "selecionar": ParamsSelecionar,
    "complementar": ParamsComplementar,
    "desconhecida": ParamsVazio,
}


class Intencao(BaseModel):
    acao: Acao
    parametros: Any
    confianca: float

    @model_validator(mode="before")
    @classmethod
    def _validar_parametros(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        acao = data.get("acao")
        parametros = data.get("parametros")
        params_cls = _ACAO_PARA_PARAMS.get(acao)  # type: ignore[arg-type]

        # function_calling pode retornar os campos de parametros no nível raiz
        if parametros is None and params_cls is not None:
            known = set(params_cls.model_fields.keys())
            extracted = {k: data[k] for k in known if k in data}
            if extracted:
                data = {k: v for k, v in data.items() if k not in known}
                parametros = extracted
                data["parametros"] = parametros

        if params_cls is not None and isinstance(parametros, dict):
            data = dict(data)
            # Raises ValidationError if shape doesn't match (extra="forbid")
            data["parametros"] = params_cls.model_validate(parametros)
        return data
