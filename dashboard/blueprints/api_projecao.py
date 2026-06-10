"""Blueprint da API de projeção de pendentes — sempre 6 meses (corrente + 5).

- GET /api/projecao — somas de PENDENTEs por mês, ignora ?periodo

Contrato: specs/melhorias-dashboard/contracts/api-json-v2.md (congelado).
"""

from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, jsonify

from app.models.enums import StatusEnum, TipoEnum
from app.repositories.transacao_repository import TransacaoRepository
from dashboard.blueprints.api_graficos import fmt_mes
from dashboard.db import SessionFactory

bp = Blueprint("api_projecao", __name__, url_prefix="/api")

_DOIS_DECIMAIS = Decimal("0.01")


def _como_str(atributo) -> str:
    """tipo/status podem vir como str ou enum do ORM — compara por valor."""
    return getattr(atributo, "value", atributo)


def _valor_json(valor: Decimal) -> str:
    return str(valor.quantize(_DOIS_DECIMAIS))


def _primeiro_dia_mes(hoje: date, meses_a_frente: int) -> date:
    """Primeiro dia do mês corrente + N meses."""
    base = hoje.year * 12 + hoje.month - 1 + meses_a_frente
    return date(base // 12, base % 12 + 1, 1)


@bp.get("/projecao")
async def projecao():
    """Projeção dos próximos 6 meses (corrente + 5), só status PENDENTE."""
    hoje = date.today()
    meses = [_primeiro_dia_mes(hoje, i) for i in range(6)]
    inicio = meses[0]
    fim = _primeiro_dia_mes(hoje, 6) - timedelta(days=1)

    async with SessionFactory() as session:
        repo = TransacaoRepository(session)
        transacoes = await repo.listar_por_periodo(inicio, fim)

    somas: dict[tuple[int, int], dict] = {
        (mes.year, mes.month): {
            "gastos": Decimal("0"),
            "receitas": Decimal("0"),
            "qtd_parcelas": 0,
        }
        for mes in meses
    }
    for t in transacoes:
        if _como_str(t.status) != StatusEnum.PENDENTE.value:
            continue
        chave = (t.data.year, t.data.month)
        if chave not in somas:
            continue
        tipo = _como_str(t.tipo)
        if tipo == TipoEnum.GASTO.value:
            somas[chave]["gastos"] += t.valor
        elif tipo == TipoEnum.RECEITA.value:
            somas[chave]["receitas"] += t.valor
        if t.parcela_total > 1:
            somas[chave]["qtd_parcelas"] += 1

    resultado = []
    for mes in meses:
        valores = somas[(mes.year, mes.month)]
        resultado.append(
            {
                "mes": fmt_mes(mes),
                "gastos_pendentes": _valor_json(valores["gastos"]),
                "receitas_pendentes": _valor_json(valores["receitas"]),
                "saldo_projetado": _valor_json(
                    valores["receitas"] - valores["gastos"]
                ),
                "qtd_parcelas": valores["qtd_parcelas"],
            }
        )
    return jsonify(resultado)
