"""Blueprint da API de resumo (RF-02) e pizza de categorias (RF-03).

Contratos: specs/dashboard-flask/contracts/{db-session,periodo,api-json,
repository-reuse}.md (congelados) + specs/melhorias-dashboard/contracts/
api-json-v2.md (resumo ganha `receitas`; `saldo = receitas - gastos`).
"""

from decimal import Decimal

from flask import Blueprint, jsonify, request

from app.models.enums import TipoEnum
from app.repositories.transacao_repository import TransacaoRepository
from dashboard.db import SessionFactory
from dashboard.periodo import resolver_periodo

bp = Blueprint("api_resumo", __name__, url_prefix="/api")

_DOIS_DECIMAIS = Decimal("0.01")


def _como_str(atributo) -> str:
    """Normaliza atributo que pode vir como str ou enum (compara pelo value)."""
    return atributo.value if hasattr(atributo, "value") else str(atributo)


def _valor_json(valor: Decimal) -> str:
    """Serializa Decimal como string com 2 casas (contrato api-json.md)."""
    return str(valor.quantize(_DOIS_DECIMAIS))


async def _listar_transacoes(periodo: str) -> list:
    inicio, fim = resolver_periodo(periodo)
    async with SessionFactory() as session:
        repo = TransacaoRepository(session)
        return await repo.listar_por_periodo(inicio, fim)


@bp.get("/resumo")
async def resumo():
    periodo = request.args.get("periodo", "mes_atual")
    transacoes = await _listar_transacoes(periodo)

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
    saldo = receitas - gastos

    return jsonify(
        {
            "gastos": _valor_json(gastos),
            "receitas": _valor_json(receitas),
            "investimentos": _valor_json(investimentos),
            "saldo": _valor_json(saldo),
            "periodo": periodo,
        }
    )


@bp.get("/grafico/categorias")
async def grafico_categorias():
    periodo = request.args.get("periodo", "mes_atual")
    transacoes = await _listar_transacoes(periodo)

    # Nao usar agregar_por_categoria: o metodo nao filtra por tipo e
    # misturaria investimentos com gastos (contrato repository-reuse.md).
    totais: dict[str, Decimal] = {}
    for t in transacoes:
        if _como_str(t.tipo) != TipoEnum.GASTO.value:
            continue
        categoria = _como_str(t.categoria)
        totais[categoria] = totais.get(categoria, Decimal("0")) + t.valor

    total_geral = sum(totais.values(), Decimal("0"))
    if total_geral == 0:
        return jsonify([])

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
    return jsonify(itens)
