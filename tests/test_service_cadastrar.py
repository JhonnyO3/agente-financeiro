import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from app.agents.extrator import ExtracaoResult
from app.agents.categorizador import CategorizacaoResult
from app.models.enums import TipoEnum, CategoriaEnum
from app.services.cadastrar import CadastrarService, ResultadoCadastro
from app.services.confirmacao_state import ConfirmacaoState


def _make_transacao_fake(id, tipo, valor, descricao, categoria, data, parcela_numero, parcela_total, grupo_parcela_id):
    t = MagicMock()
    t.id = id
    t.tipo = tipo
    t.valor = valor
    t.descricao = descricao
    t.categoria = categoria
    t.data = data
    t.parcela_numero = parcela_numero
    t.parcela_total = parcela_total
    t.grupo_parcela_id = str(grupo_parcela_id)
    return t


def _make_service(extracao_result, categorizacao_result, embedding_result=None, criar_lote_result=None):
    extrator = MagicMock()
    extrator.extrair = AsyncMock(return_value=extracao_result)

    categorizador = MagicMock()
    categorizador.categorizar = AsyncMock(return_value=categorizacao_result)

    embedder = MagicMock()
    embedder.gerar_para_transacao = AsyncMock(return_value=embedding_result or [0.1] * 1536)

    repository = MagicMock()
    repository.criar_lote = AsyncMock(return_value=criar_lote_result or [])

    confirmacao_state = ConfirmacaoState()

    service = CadastrarService(
        repository=repository,
        embedder=embedder,
        extrator=extrator,
        categorizador=categorizador,
        confirmacao_state=confirmacao_state,
    )
    return service, extrator, categorizador, embedder, repository, confirmacao_state


@pytest.mark.asyncio
async def test_gasto_simples_uma_transacao():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("45.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="mercado",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    categorizacao = CategorizacaoResult(categoria="ALIMENTACAO")

    transacao_fake = _make_transacao_fake(1, "GASTO", Decimal("45.00"), "mercado", "ALIMENTACAO", hoje, 1, 1, __import__("uuid").uuid4())
    service, extrator, _, embedder, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=[transacao_fake])

    resultado = await service.executar("gastei 45 no mercado", "5511999999999")

    assert resultado.aguarda_confirmacao is False
    assert len(resultado.transacoes) == 1
    assert resultado.transacoes[0].parcela_total == 1

    lote_chamado = repository.criar_lote.call_args[0][0]
    assert len(lote_chamado) == 1
    assert lote_chamado[0].valor == Decimal("45.00")
    assert lote_chamado[0].parcela_numero == 1
    assert lote_chamado[0].parcela_total == 1


@pytest.mark.asyncio
async def test_seis_parcelas_mesmo_grupo_datas_corretas():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("900.00"),
        valor_por_parcela=Decimal("150.00"),
        parcela_total=6,
        descricao="celular",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    categorizacao = CategorizacaoResult(categoria="COMPRAS")

    transacoes_fake = [
        _make_transacao_fake(i + 1, "GASTO", Decimal("150.00"), "celular", "COMPRAS", hoje + timedelta(days=30 * i), i + 1, 6, __import__("uuid").uuid4())
        for i in range(6)
    ]
    service, _, _, embedder, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=transacoes_fake)

    resultado = await service.executar("celular 6x de 150", "5511999999999")

    assert resultado.aguarda_confirmacao is False
    assert len(resultado.transacoes) == 6

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 6

    grupo_id = lote[0].grupo_parcela_id
    for i, t in enumerate(lote):
        assert t.grupo_parcela_id == grupo_id
        assert t.parcela_numero == i + 1
        assert t.data == hoje + timedelta(days=30 * i)

    embedder.gerar_para_transacao.assert_called_once()


@pytest.mark.asyncio
async def test_valor_calculado_por_parcela():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("900.00"),
        valor_por_parcela=None,
        parcela_total=6,
        descricao="notebook",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    categorizacao = CategorizacaoResult(categoria="COMPRAS")

    transacoes_fake = [MagicMock() for _ in range(6)]
    service, _, _, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=transacoes_fake)

    resultado = await service.executar("900 em 6x", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 6
    for t in lote[:-1]:
        assert t.valor == Decimal("150.00")
    assert lote[-1].valor == Decimal("150.00")


@pytest.mark.asyncio
async def test_menciona_cartao_aguarda_confirmacao():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("200.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="compra",
        data_referencia=hoje,
        menciona_cartao=True,
    )
    categorizacao = CategorizacaoResult(categoria="COMPRAS")

    service, _, _, _, repository, _ = _make_service(extracao, categorizacao)

    resultado = await service.executar("comprei no cartão", "5511999999999")

    assert resultado.aguarda_confirmacao is True
    assert resultado.pergunta is not None
    assert len(resultado.transacoes) == 0
    repository.criar_lote.assert_not_called()


@pytest.mark.asyncio
async def test_divisao_nao_exata_ultimo_centavo():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("100.00"),
        valor_por_parcela=None,
        parcela_total=3,
        descricao="curso",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    categorizacao = CategorizacaoResult(categoria="GASTOS_FIXOS")

    transacoes_fake = [MagicMock() for _ in range(3)]
    service, _, _, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=transacoes_fake)

    resultado = await service.executar("100 em 3x", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 3
    assert lote[0].valor == Decimal("33.33")
    assert lote[1].valor == Decimal("33.33")
    assert lote[2].valor == Decimal("33.34")

    total = sum(t.valor for t in lote)
    assert total == Decimal("100.00")
