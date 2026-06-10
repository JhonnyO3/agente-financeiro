import calendar
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.filtro_consulta import FiltroConsultaResult
from app.models.enums import CategoriaEnum, TipoEnum
from app.repositories.dtos import AgregadoCategoria
from app.services.consultar import ConsultarService, ParcelaStatus, ResultadoConsulta


def make_service(repository=None, filtro_chain=None, embedder=None):
    repository = repository or AsyncMock()
    filtro_chain = filtro_chain or AsyncMock()
    embedder = embedder or AsyncMock()
    return ConsultarService(repository, filtro_chain, embedder)


def make_transacao(
    parcela_numero=1,
    parcela_total=1,
    valor=Decimal("100.00"),
    data=date(2026, 6, 1),
    categoria=CategoriaEnum.COMPRAS,
    tipo=TipoEnum.GASTO,
    grupo_parcela_id=None,
):
    t = MagicMock()
    t.parcela_numero = parcela_numero
    t.parcela_total = parcela_total
    t.valor = valor
    t.data = data
    t.categoria = categoria
    t.tipo = tipo
    t.grupo_parcela_id = grupo_parcela_id or uuid4()
    return t


@pytest.mark.asyncio
async def test_consulta_mensal_totais_em_decimal():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="mensal",
        mes=6,
        ano=2026,
    )

    lista = [
        AgregadoCategoria(categoria=CategoriaEnum.ALIMENTACAO, total=Decimal("150.00"), quantidade=3),
        AgregadoCategoria(categoria=CategoriaEnum.INVESTIMENTO, total=Decimal("500.00"), quantidade=1),
    ]
    repository.agregar_por_categoria.return_value = lista

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("resumo de junho")

    assert resultado.tipo == "mensal"
    assert resultado.periodo_label == "06/2026"
    assert isinstance(resultado.total_gastos, Decimal)
    assert isinstance(resultado.total_investimentos, Decimal)
    assert isinstance(resultado.total_receitas, Decimal)
    assert isinstance(resultado.balanco, Decimal)
    assert resultado.total_gastos == Decimal("150.00")
    assert resultado.total_investimentos == Decimal("500.00")
    assert resultado.total_receitas == Decimal("0")
    assert resultado.balanco == Decimal("-150.00")


@pytest.mark.asyncio
async def test_consulta_mensal_com_os_tres_totais_e_balanco():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="mensal",
        mes=6,
        ano=2026,
    )

    lista = [
        AgregadoCategoria(categoria=CategoriaEnum.ALIMENTACAO, total=Decimal("350.00"), quantidade=2),
        AgregadoCategoria(categoria=CategoriaEnum.RECEITA, total=Decimal("5000.00"), quantidade=1),
        AgregadoCategoria(categoria=CategoriaEnum.INVESTIMENTO, total=Decimal("500.00"), quantidade=1),
    ]
    repository.agregar_por_categoria.return_value = lista

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("resumo de junho")

    assert resultado.total_gastos == Decimal("350.00")
    assert resultado.total_receitas == Decimal("5000.00")
    assert resultado.total_investimentos == Decimal("500.00")
    assert resultado.balanco == Decimal("4650.00")


@pytest.mark.asyncio
async def test_consulta_mensal_receita_nao_entra_em_gastos():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="mensal",
        mes=6,
        ano=2026,
    )

    lista = [
        AgregadoCategoria(categoria=CategoriaEnum.RECEITA, total=Decimal("1000.00"), quantidade=1),
    ]
    repository.agregar_por_categoria.return_value = lista

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("resumo de junho")

    assert resultado.total_gastos == Decimal("0")
    assert resultado.total_receitas == Decimal("1000.00")
    assert resultado.balanco == Decimal("1000.00")


@pytest.mark.asyncio
async def test_consulta_mensal_sem_receitas_balanco_negativo():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="mensal",
        mes=6,
        ano=2026,
    )

    lista = [
        AgregadoCategoria(categoria=CategoriaEnum.COMPRAS, total=Decimal("200.00"), quantidade=1),
    ]
    repository.agregar_por_categoria.return_value = lista

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("resumo de junho")

    assert resultado.total_gastos == Decimal("200.00")
    assert resultado.total_receitas == Decimal("0")
    assert resultado.balanco == Decimal("-200.00")


@pytest.mark.asyncio
async def test_consulta_semanal_com_receitas_e_balanco():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="semanal",
    )

    lista = [
        AgregadoCategoria(categoria=CategoriaEnum.LAZER, total=Decimal("80.00"), quantidade=1),
        AgregadoCategoria(categoria=CategoriaEnum.RECEITA, total=Decimal("300.00"), quantidade=1),
    ]
    repository.agregar_por_categoria.return_value = lista

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("resumo da semana")

    assert resultado.total_gastos == Decimal("80.00")
    assert resultado.total_receitas == Decimal("300.00")
    assert resultado.balanco == Decimal("220.00")


@pytest.mark.asyncio
async def test_consulta_geral_com_receitas_e_balanco():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="geral",
    )

    lista = [
        AgregadoCategoria(categoria=CategoriaEnum.TRANSPORTE, total=Decimal("120.00"), quantidade=2),
        AgregadoCategoria(categoria=CategoriaEnum.RECEITA, total=Decimal("2000.00"), quantidade=1),
        AgregadoCategoria(categoria=CategoriaEnum.INVESTIMENTO, total=Decimal("400.00"), quantidade=1),
    ]
    repository.agregar_por_categoria.return_value = lista

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("resumo geral")

    assert resultado.tipo == "geral"
    assert resultado.total_gastos == Decimal("120.00")
    assert resultado.total_receitas == Decimal("2000.00")
    assert resultado.total_investimentos == Decimal("400.00")
    assert resultado.balanco == Decimal("1880.00")


def test_resultado_consulta_defaults_de_receitas_e_balanco():
    resultado = ResultadoConsulta(
        tipo="mensal",
        periodo_label="06/2026",
        total_gastos=Decimal("10.00"),
        total_investimentos=Decimal("0"),
        por_categoria=[],
    )
    assert resultado.total_receitas == Decimal("0")
    assert resultado.balanco == Decimal("0")


@pytest.mark.asyncio
async def test_consulta_semanal_inicio_e_segunda_feira():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="semanal",
    )

    repository.agregar_por_categoria.return_value = []

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("quanto gastei essa semana")

    assert resultado.tipo == "semanal"

    hoje = date.today()
    esperado_inicio = hoje - timedelta(days=hoje.weekday())
    esperado_fim = esperado_inicio + timedelta(days=6)

    call_args = repository.agregar_por_categoria.call_args
    inicio_chamado, fim_chamado = call_args[0]
    assert inicio_chamado == esperado_inicio
    assert fim_chamado == esperado_fim
    assert esperado_inicio.weekday() == 0


@pytest.mark.asyncio
async def test_consulta_grupo_parcela_lista_com_status_correto():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="grupo_parcela",
        descricao_grupo="celular",
    )

    embedder.gerar.return_value = [0.1] * 1536

    grupo_id = uuid4()
    transacao_ref = make_transacao(grupo_parcela_id=grupo_id)
    repository.buscar_semantico_com_distancia.return_value = (transacao_ref, 0.3)

    hoje = date.today()
    fim_mes = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])

    data_paga = hoje - timedelta(days=5)
    data_proxima = hoje if hoje <= fim_mes else fim_mes
    data_futura = fim_mes + timedelta(days=10)

    parcelas_raw = [
        make_transacao(parcela_numero=1, parcela_total=3, valor=Decimal("200.00"), data=data_paga, grupo_parcela_id=grupo_id),
        make_transacao(parcela_numero=2, parcela_total=3, valor=Decimal("200.00"), data=data_proxima, grupo_parcela_id=grupo_id),
        make_transacao(parcela_numero=3, parcela_total=3, valor=Decimal("200.00"), data=data_futura, grupo_parcela_id=grupo_id),
    ]
    repository.buscar_por_grupo.return_value = parcelas_raw

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("parcelas do celular")

    assert resultado.tipo == "grupo_parcela"
    assert resultado.total_receitas == Decimal("0")
    assert resultado.balanco == Decimal("0")
    assert resultado.parcelas is not None
    assert len(resultado.parcelas) == 3

    statuses = [p.status for p in resultado.parcelas]
    assert statuses[0] == "Paga"
    assert statuses[2] == "Futura"


@pytest.mark.asyncio
async def test_parcela_com_data_anterior_a_hoje_e_paga():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="grupo_parcela",
        descricao_grupo="notebook",
    )
    embedder.gerar.return_value = [0.1] * 1536

    grupo_id = uuid4()
    transacao_ref = make_transacao(grupo_parcela_id=grupo_id)
    repository.buscar_semantico_com_distancia.return_value = (transacao_ref, 0.2)

    hoje = date.today()
    data_passada = hoje - timedelta(days=30)

    parcela_raw = make_transacao(
        parcela_numero=1,
        parcela_total=2,
        valor=Decimal("300.00"),
        data=data_passada,
        grupo_parcela_id=grupo_id,
    )
    repository.buscar_por_grupo.return_value = [parcela_raw]

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("parcelas do notebook")

    assert resultado.parcelas is not None
    assert len(resultado.parcelas) == 1
    assert resultado.parcelas[0].status == "Paga"


@pytest.mark.asyncio
async def test_parcela_no_mes_atual_e_nao_passou_e_proxima():
    repository = AsyncMock()
    filtro_chain = AsyncMock()
    embedder = AsyncMock()

    filtro_chain.extrair.return_value = FiltroConsultaResult(
        tipo_consulta="grupo_parcela",
        descricao_grupo="tablet",
    )
    embedder.gerar.return_value = [0.1] * 1536

    grupo_id = uuid4()
    transacao_ref = make_transacao(grupo_parcela_id=grupo_id)
    repository.buscar_semantico_com_distancia.return_value = (transacao_ref, 0.1)

    hoje = date.today()
    fim_mes = date(hoje.year, hoje.month, calendar.monthrange(hoje.year, hoje.month)[1])

    parcela_raw = make_transacao(
        parcela_numero=1,
        parcela_total=1,
        valor=Decimal("450.00"),
        data=fim_mes,
        grupo_parcela_id=grupo_id,
    )
    repository.buscar_por_grupo.return_value = [parcela_raw]

    service = make_service(repository, filtro_chain, embedder)
    resultado = await service.executar("parcelas do tablet")

    assert resultado.parcelas is not None
    assert len(resultado.parcelas) == 1
    assert resultado.parcelas[0].status == "Próxima"
