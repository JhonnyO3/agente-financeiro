from datetime import date
from decimal import Decimal

from backend.repositories.transacao_repository import TransacaoRepository
from backend.dtos.graficos import ProjecaoMes
from backend.services.graficos import _como_str, _valor_str, fmt_mes
from backend.services.janela import janela_meses, ultimo_dia


class ProjecaoService:
    def __init__(self, repo: TransacaoRepository) -> None:
        self._repo = repo

    async def projecao(self, hoje: date) -> list[ProjecaoMes]:
        meses = janela_meses(hoje)[6:]
        transacoes = await self._repo.listar_por_periodo(meses[0], ultimo_dia(meses[-1]))

        somas: dict[tuple[int, int], dict] = {
            (mes.year, mes.month): {
                "gastos": Decimal("0"),
                "receitas": Decimal("0"),
                "investimentos": Decimal("0"),
                "qtd_parcelas": 0,
            }
            for mes in meses
        }
        for t in transacoes:
            chave = (t.data.year, t.data.month)
            if chave not in somas:
                continue
            tipo = _como_str(t.tipo)
            if tipo == "GASTO":
                somas[chave]["gastos"] += t.valor
            elif tipo == "RECEITA":
                somas[chave]["receitas"] += t.valor
            elif tipo == "INVESTIMENTO":
                somas[chave]["investimentos"] += t.valor
            if t.parcela_total > 1:
                somas[chave]["qtd_parcelas"] += 1

        resultado = []
        for mes in meses:
            valores = somas[(mes.year, mes.month)]
            sem_movimento = (
                valores["gastos"] == 0
                and valores["receitas"] == 0
                and valores["investimentos"] == 0
                and valores["qtd_parcelas"] == 0
            )
            if sem_movimento:
                continue
            resultado.append(
                ProjecaoMes(
                    mes=fmt_mes(mes),
                    gastos=_valor_str(valores["gastos"]),
                    receitas=_valor_str(valores["receitas"]),
                    investimentos=_valor_str(valores["investimentos"]),
                    saldo=_valor_str(
                        valores["receitas"] - valores["gastos"] - valores["investimentos"]
                    ),
                    qtd_parcelas=valores["qtd_parcelas"],
                )
            )
        return resultado
