from collections import defaultdict
from datetime import date
from decimal import Decimal

from backend.repositories.transacao_repository import TransacaoRepository
from backend.dtos.graficos import CATEGORIAS_GASTO, EvolucaoMes
from backend.services.janela import janela_meses, ultimo_dia
from backend.services.recorrencia import chave_recorrencia, consolidar_templates

_BUCKET_POR_TIPO = {
    "GASTO": "gastos",
    "INVESTIMENTO": "investimentos",
    "RECEITA": "receitas",
}

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

_CENTAVOS = Decimal("0.01")


def fmt_mes(d: date) -> str:
    return f"{MESES_PT[d.month - 1]}/{str(d.year)[2:]}"


def _valor_str(valor: Decimal) -> str:
    return str(valor.quantize(_CENTAVOS))


def _como_str(atributo) -> str:
    return getattr(atributo, "value", atributo)


class GraficosService:
    def __init__(self, repo: TransacaoRepository) -> None:
        self._repo = repo

    async def mensal(self, hoje: date, usuario_id: int) -> list[dict]:
        meses = janela_meses(hoje)
        mes_atual = meses[6]
        transacoes = await self._repo.listar_por_periodo(
            meses[0], ultimo_dia(meses[-1]), usuario_id=usuario_id
        )
        templates = consolidar_templates(
            await self._repo.listar_recorrentes(usuario_id)
        )

        somas: dict[tuple[int, int], dict[str, Decimal]] = defaultdict(
            lambda: defaultdict(lambda: Decimal("0"))
        )
        materializadas: dict[tuple[int, int], set] = defaultdict(set)
        for t in transacoes:
            if _como_str(t.tipo) != "GASTO":
                continue
            chave = (t.data.year, t.data.month)
            somas[chave][_como_str(t.categoria)] += t.valor
            materializadas[chave].add(chave_recorrencia(t))

        for mes in meses:
            if mes < mes_atual:
                continue
            chave = (mes.year, mes.month)
            for chave_t, template in templates.items():
                if _como_str(template.tipo) != "GASTO":
                    continue
                if chave_t in materializadas[chave]:
                    continue
                somas[chave][_como_str(template.categoria)] += template.valor

        resultado = []
        for mes in meses:
            por_categoria = somas.get((mes.year, mes.month))
            if not por_categoria or sum(por_categoria.values()) == 0:
                continue
            item = {"mes": fmt_mes(mes)}
            for categoria in CATEGORIAS_GASTO:
                item[categoria] = _valor_str(por_categoria[categoria])
            resultado.append(item)
        return resultado

    async def heatmap_mes(self, mes_ref: date, usuario_id: int) -> list[dict]:
        from calendar import monthrange
        inicio = mes_ref.replace(day=1)
        _, dias_no_mes = monthrange(mes_ref.year, mes_ref.month)
        fim = mes_ref.replace(day=dias_no_mes)

        transacoes = await self._repo.listar_por_periodo(inicio, fim, usuario_id=usuario_id)

        somas: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
        for t in transacoes:
            if _como_str(t.tipo) == "GASTO":
                somas[t.data.day] += t.valor

        result = []
        for dia in range(1, dias_no_mes + 1):
            d = mes_ref.replace(day=dia)
            result.append({
                "dia": dia,
                "dia_semana": d.weekday(),  # 0=seg … 6=dom
                "total": _valor_str(somas[dia]),
            })
        return result

    async def evolucao(self, hoje: date, usuario_id: int) -> list[EvolucaoMes]:
        meses = janela_meses(hoje)
        mes_atual = meses[6]
        transacoes = await self._repo.listar_por_periodo(
            meses[0], ultimo_dia(meses[-1]), usuario_id=usuario_id
        )
        templates = consolidar_templates(
            await self._repo.listar_recorrentes(usuario_id)
        )

        somas: dict[tuple[int, int], dict[str, Decimal]] = defaultdict(
            lambda: {
                "gastos": Decimal("0"),
                "investimentos": Decimal("0"),
                "receitas": Decimal("0"),
            }
        )
        materializadas: dict[tuple[int, int], set] = defaultdict(set)
        for t in transacoes:
            bucket = _BUCKET_POR_TIPO.get(_como_str(t.tipo))
            if bucket is None:
                continue
            chave = (t.data.year, t.data.month)
            somas[chave][bucket] += t.valor
            materializadas[chave].add(chave_recorrencia(t))

        for mes in meses:
            if mes < mes_atual:
                continue
            chave = (mes.year, mes.month)
            for chave_t, template in templates.items():
                bucket = _BUCKET_POR_TIPO.get(_como_str(template.tipo))
                if bucket is None or chave_t in materializadas[chave]:
                    continue
                somas[chave][bucket] += template.valor

        return [
            EvolucaoMes(
                mes=fmt_mes(mes),
                gastos=_valor_str(somas[(mes.year, mes.month)]["gastos"]),
                investimentos=_valor_str(somas[(mes.year, mes.month)]["investimentos"]),
                receitas=_valor_str(somas[(mes.year, mes.month)]["receitas"]),
            )
            for mes in meses
        ]
