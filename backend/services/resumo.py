from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TipoEnum
from app.repositories.transacao_repository import TransacaoRepository

_DOIS_DECIMAIS = Decimal("0.01")
_DATA_PISO = date(2000, 1, 1)
_DATA_TETO = date(2100, 1, 1)


def _ultimo_dia_mes(d: date) -> date:
    prox = date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)
    return prox - timedelta(days=1)


def resolver_periodo(periodo: str) -> tuple[date, date]:
    hoje = date.today()
    fim_mes = _ultimo_dia_mes(hoje)

    if periodo == "mes_anterior":
        primeiro_mes_atual = date(hoje.year, hoje.month, 1)
        ultimo_mes_anterior = primeiro_mes_atual - timedelta(days=1)
        inicio = date(ultimo_mes_anterior.year, ultimo_mes_anterior.month, 1)
        return inicio, ultimo_mes_anterior

    if periodo == "ultimos_3_meses":
        return hoje - timedelta(days=90), fim_mes

    if periodo == "ultimos_6_meses":
        return hoje - timedelta(days=180), fim_mes

    if periodo == "ano_atual":
        return date(hoje.year, 1, 1), date(hoje.year, 12, 31)

    if periodo == "tudo":
        return _DATA_PISO, _DATA_TETO

    return date(hoje.year, hoje.month, 1), fim_mes


def _como_str(atributo) -> str:
    return atributo.value if hasattr(atributo, "value") else str(atributo)


def _valor_json(valor: Decimal) -> str:
    return str(valor.quantize(_DOIS_DECIMAIS))


async def _listar(session: AsyncSession, periodo: str) -> list:
    inicio, fim = resolver_periodo(periodo)
    repo = TransacaoRepository(session)
    return await repo.listar_por_periodo(inicio, fim)


async def calcular_resumo(session: AsyncSession, periodo: str) -> dict:
    transacoes = await _listar(session, periodo)

    gastos = sum(
        (t.valor for t in transacoes if _como_str(t.tipo) == TipoEnum.GASTO.value),
        Decimal("0"),
    )
    receitas = sum(
        (t.valor for t in transacoes if _como_str(t.tipo) == TipoEnum.RECEITA.value),
        Decimal("0"),
    )
    investimentos = sum(
        (
            t.valor
            for t in transacoes
            if _como_str(t.tipo) == TipoEnum.INVESTIMENTO.value
        ),
        Decimal("0"),
    )
    saldo = receitas - gastos - investimentos

    return {
        "gastos": _valor_json(gastos),
        "receitas": _valor_json(receitas),
        "investimentos": _valor_json(investimentos),
        "saldo": _valor_json(saldo),
        "periodo": periodo,
    }


async def categorias_gasto(session: AsyncSession, periodo: str) -> list[dict]:
    transacoes = await _listar(session, periodo)

    totais: dict[str, Decimal] = {}
    for t in transacoes:
        if _como_str(t.tipo) != TipoEnum.GASTO.value:
            continue
        categoria = _como_str(t.categoria)
        totais[categoria] = totais.get(categoria, Decimal("0")) + t.valor

    total_geral = sum(totais.values(), Decimal("0"))
    if total_geral == 0:
        return []

    itens = [
        {
            "categoria": categoria,
            "total": _valor_json(total),
            "percentual": round(float(total / total_geral * 100), 2),
        }
        for categoria, total in totais.items()
        if total > 0
    ]
    itens.sort(key=lambda item: Decimal(item["total"]), reverse=True)
    return itens
