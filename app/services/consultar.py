import calendar
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, timedelta
from typing import Literal

from app.models.enums import CategoriaEnum


@dataclass
class ParcelaStatus:
    parcela_numero: int
    parcela_total: int
    valor: Decimal
    data: date
    status: Literal["Paga", "Próxima", "Futura"]


@dataclass
class ResultadoConsulta:
    tipo: str
    periodo_label: str
    total_gastos: Decimal
    total_investimentos: Decimal
    por_categoria: list
    parcelas: list | None = None


class ConsultarService:
    def __init__(self, repository, filtro_chain, embedder):
        self._repository = repository
        self._filtro_chain = filtro_chain
        self._embedder = embedder

    async def executar(self, mensagem: str) -> ResultadoConsulta:
        filtro = await self._filtro_chain.extrair(mensagem, date.today())

        if filtro.tipo_consulta == "mensal":
            return await self._consulta_mensal(filtro)
        elif filtro.tipo_consulta == "semanal":
            return await self._consulta_semanal()
        elif filtro.tipo_consulta == "grupo_parcela":
            return await self._consulta_grupo_parcela(filtro)
        else:
            return await self._consulta_geral()

    async def _consulta_mensal(self, filtro) -> ResultadoConsulta:
        M = filtro.mes
        A = filtro.ano
        inicio = date(A, M, 1)
        fim = date(A, M, calendar.monthrange(A, M)[1])
        lista = await self._repository.agregar_por_categoria(inicio, fim)
        total_gastos = sum(
            (a.total for a in lista if a.categoria != CategoriaEnum.INVESTIMENTO),
            Decimal("0"),
        )
        total_investimentos = sum(
            (a.total for a in lista if a.categoria == CategoriaEnum.INVESTIMENTO),
            Decimal("0"),
        )
        return ResultadoConsulta(
            tipo="mensal",
            periodo_label=f"{M:02d}/{A}",
            total_gastos=total_gastos,
            total_investimentos=total_investimentos,
            por_categoria=lista,
        )

    async def _consulta_semanal(self) -> ResultadoConsulta:
        hoje = date.today()
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
        lista = await self._repository.agregar_por_categoria(inicio, fim)
        total_gastos = sum(
            (a.total for a in lista if a.categoria != CategoriaEnum.INVESTIMENTO),
            Decimal("0"),
        )
        total_investimentos = sum(
            (a.total for a in lista if a.categoria == CategoriaEnum.INVESTIMENTO),
            Decimal("0"),
        )
        inicio_label = inicio.strftime("%d/%m")
        fim_label = fim.strftime("%d/%m")
        return ResultadoConsulta(
            tipo="semanal",
            periodo_label=f"{inicio_label} – {fim_label}",
            total_gastos=total_gastos,
            total_investimentos=total_investimentos,
            por_categoria=lista,
        )

    async def _consulta_grupo_parcela(self, filtro) -> ResultadoConsulta:
        descricao_grupo = filtro.descricao_grupo
        vetor = await self._embedder.gerar(descricao_grupo)
        resultado = await self._repository.buscar_semantico_com_distancia(vetor, 1)

        if resultado is None or resultado[1] > 1.0:
            return ResultadoConsulta(
                tipo="grupo_parcela",
                periodo_label=descricao_grupo or "",
                total_gastos=Decimal("0"),
                total_investimentos=Decimal("0"),
                por_categoria=[],
                parcelas=[],
            )

        transacao, _ = resultado
        parcelas_raw = await self._repository.buscar_por_grupo(transacao.grupo_parcela_id)

        hoje = date.today()
        fim_mes = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])

        parcelas = []
        for p in parcelas_raw:
            if p.data < hoje:
                status = "Paga"
            elif p.data <= fim_mes:
                status = "Próxima"
            else:
                status = "Futura"
            parcelas.append(
                ParcelaStatus(
                    parcela_numero=p.parcela_numero,
                    parcela_total=p.parcela_total,
                    valor=p.valor,
                    data=p.data,
                    status=status,
                )
            )

        return ResultadoConsulta(
            tipo="grupo_parcela",
            periodo_label=descricao_grupo or "",
            total_gastos=Decimal("0"),
            total_investimentos=Decimal("0"),
            por_categoria=[],
            parcelas=parcelas,
        )

    async def _consulta_geral(self) -> ResultadoConsulta:
        inicio = date(2000, 1, 1)
        fim = date.today()
        lista = await self._repository.agregar_por_categoria(inicio, fim)
        total_gastos = sum(
            (a.total for a in lista if a.categoria != CategoriaEnum.INVESTIMENTO),
            Decimal("0"),
        )
        total_investimentos = sum(
            (a.total for a in lista if a.categoria == CategoriaEnum.INVESTIMENTO),
            Decimal("0"),
        )
        return ResultadoConsulta(
            tipo="geral",
            periodo_label="geral",
            total_gastos=total_gastos,
            total_investimentos=total_investimentos,
            por_categoria=lista,
        )
