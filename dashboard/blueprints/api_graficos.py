"""Blueprint dos gráficos temporais do dashboard (RF-04, RF-05).

- GET /api/grafico/mensal   — barras por categoria, sempre últimos 6 meses
- GET /api/grafico/evolucao — linha gastos x investimentos, todos os meses com dados

Contratos: db-session.md, api-json.md, repository-reuse.md (congelados).
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from flask import Blueprint, jsonify

from app.repositories.transacao_repository import TransacaoRepository
from dashboard.db import SessionFactory

bp = Blueprint("api_graficos", __name__, url_prefix="/api/grafico")

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# As 7 categorias de gasto — INVESTIMENTO fica de fora (gráfico só de gastos)
CATEGORIAS_GASTO = (
    "ALIMENTACAO",
    "TRANSPORTE",
    "LAZER",
    "GASTOS_FIXOS",
    "COMPRAS",
    "GASTOS_PONTUAIS",
    "OUTROS",
)

_CENTAVOS = Decimal("0.01")


def fmt_mes(d: date) -> str:
    return f"{MESES_PT[d.month - 1]}/{str(d.year)[2:]}"


def _valor_str(valor: Decimal) -> str:
    return str(valor.quantize(_CENTAVOS))


def _como_str(atributo) -> str:
    """tipo/categoria podem vir como str ou enum do ORM — compara por valor."""
    return getattr(atributo, "value", atributo)


def _ultimos_6_meses(hoje: date) -> list[date]:
    """Primeiro dia de cada um dos últimos 6 meses, em ordem crescente."""
    base = hoje.year * 12 + hoje.month - 1 - 5
    return [date((base + i) // 12, (base + i) % 12 + 1, 1) for i in range(6)]


@bp.get("/mensal")
async def mensal():
    """Soma de gastos por categoria nos últimos 6 meses. Ignora ?periodo."""
    hoje = date.today()
    meses = _ultimos_6_meses(hoje)

    async with SessionFactory() as session:
        repo = TransacaoRepository(session)
        transacoes = await repo.listar_por_periodo(meses[0], hoje)

    somas: dict[tuple[int, int], dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: Decimal("0"))
    )
    for t in transacoes:
        if _como_str(t.tipo) != "GASTO":
            continue
        somas[(t.data.year, t.data.month)][_como_str(t.categoria)] += t.valor

    resultado = []
    for mes in meses:
        por_categoria = somas[(mes.year, mes.month)]
        item = {"mes": fmt_mes(mes)}
        for categoria in CATEGORIAS_GASTO:
            item[categoria] = _valor_str(por_categoria[categoria])
        resultado.append(item)
    return jsonify(resultado)


@bp.get("/evolucao")
async def evolucao():
    """Gastos e investimentos por mês — apenas meses com pelo menos 1 registro."""
    async with SessionFactory() as session:
        repo = TransacaoRepository(session)
        transacoes = await repo.listar_por_periodo(date(2000, 1, 1), date.today())

    somas: dict[tuple[int, int], dict[str, Decimal]] = defaultdict(
        lambda: {"gastos": Decimal("0"), "investimentos": Decimal("0")}
    )
    for t in transacoes:
        chave = "gastos" if _como_str(t.tipo) == "GASTO" else "investimentos"
        somas[(t.data.year, t.data.month)][chave] += t.valor

    resultado = [
        {
            "mes": fmt_mes(date(ano, mes, 1)),
            "gastos": _valor_str(valores["gastos"]),
            "investimentos": _valor_str(valores["investimentos"]),
        }
        for (ano, mes), valores in sorted(somas.items())
    ]
    return jsonify(resultado)
