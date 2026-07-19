from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dtos.preferencias import PreferenciasBody, PreferenciasResponse
from backend.models.enums import TipoEnum
from backend.repositories.preferencias_repository import PreferenciasRepository
from backend.repositories.transacao_repository import TransacaoRepository
from backend.services.resumo import resolver_periodo

_DOIS_DECIMAIS = Decimal("0.01")
_TIPOS_SAIDA = {TipoEnum.GASTO.value, TipoEnum.INVESTIMENTO.value}


class ValidacaoError(Exception):
    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


def _como_str(atributo) -> str:
    return atributo.value if hasattr(atributo, "value") else str(atributo)


def _valor_json(valor: Decimal) -> str:
    return str(valor.quantize(_DOIS_DECIMAIS))


def _pct(valor: Decimal) -> float:
    return round(float(valor), 2)


async def obter(session: AsyncSession, usuario_id: int) -> dict:
    repo = PreferenciasRepository(session)
    preferencias = await repo.obter(usuario_id)
    if preferencias is None:
        return {}
    return PreferenciasResponse.de_modelo(preferencias).model_dump()


async def salvar(session: AsyncSession, usuario_id: int, body: dict) -> dict:
    try:
        dados = PreferenciasBody.model_validate(body)
    except ValidationError as erro:
        raise ValidacaoError(erro.errors()[0]["msg"])

    metas = {categoria: float(pct) for categoria, pct in dados.metas.items()}
    repo = PreferenciasRepository(session)
    preferencias = await repo.upsert(usuario_id, dados.renda_mensal, metas)
    return PreferenciasResponse.de_modelo(preferencias).model_dump()


async def aderencia(session: AsyncSession, usuario_id: int, periodo: str) -> list[dict]:
    prefs_repo = PreferenciasRepository(session)
    preferencias = await prefs_repo.obter(usuario_id)
    if preferencias is None or not preferencias.metas:
        return []

    inicio, fim = resolver_periodo(periodo)
    repo = TransacaoRepository(session)
    transacoes = await repo.listar_por_periodo(inicio, fim, usuario_id=usuario_id)

    total_saidas = Decimal("0")
    por_categoria: dict[str, Decimal] = {}
    for t in transacoes:
        if _como_str(t.tipo) not in _TIPOS_SAIDA:
            continue
        categoria = _como_str(t.categoria)
        por_categoria[categoria] = por_categoria.get(categoria, Decimal("0")) + t.valor
        total_saidas += t.valor

    itens = []
    for categoria, meta in preferencias.metas.items():
        meta_pct = Decimal(str(meta))
        realizado_valor = por_categoria.get(categoria, Decimal("0"))
        realizado_pct = (
            realizado_valor / total_saidas * Decimal("100")
            if total_saidas > 0
            else Decimal("0")
        )
        desvio_pct = realizado_pct - meta_pct
        itens.append(
            {
                "categoria": categoria,
                "meta_pct": _pct(meta_pct),
                "realizado_valor": _valor_json(realizado_valor),
                "realizado_pct": _pct(realizado_pct),
                "desvio_pct": _pct(desvio_pct),
            }
        )
    return itens
