from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call
from uuid import UUID, uuid4

import pytest

from app.models.enums import CategoriaEnum, TipoEnum
from app.repositories.dtos import TransacaoCreate, TransacaoUpdate
from app.repositories.transacao_repository import TransacaoRepository


def make_dto(**kwargs) -> TransacaoCreate:
    defaults = dict(
        tipo=TipoEnum.GASTO,
        valor=Decimal("50.00"),
        descricao="mercado",
        categoria=CategoriaEnum.ALIMENTACAO,
        data=date(2026, 6, 9),
        parcela_numero=1,
        parcela_total=1,
        grupo_parcela_id=uuid4(),
        embedding=[0.1] * 1536,
    )
    defaults.update(kwargs)
    return TransacaoCreate(**defaults)


@pytest.mark.asyncio
async def test_criar_chama_add_e_flush():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TransacaoRepository(session)
    dto = make_dto()
    await repo.criar(dto)

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_criar_persiste_campos_novos():
    from app.models.enums import FormaPagamentoEnum, StatusEnum

    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TransacaoRepository(session)
    dto = make_dto(
        status=StatusEnum.PAGO,
        forma_pagamento=FormaPagamentoEnum.PIX,
        responsavel="Mãe",
        detalhes="compra do mês",
    )
    await repo.criar(dto)

    obj = session.add.call_args[0][0]
    assert obj.status == StatusEnum.PAGO
    assert obj.forma_pagamento == FormaPagamentoEnum.PIX
    assert obj.responsavel == "Mãe"
    assert obj.detalhes == "compra do mês"


@pytest.mark.asyncio
async def test_criar_sem_campos_novos_usa_defaults_do_dto():
    from app.models.enums import FormaPagamentoEnum, StatusEnum

    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TransacaoRepository(session)
    await repo.criar(make_dto())

    obj = session.add.call_args[0][0]
    assert obj.status == StatusEnum.PENDENTE
    assert obj.forma_pagamento == FormaPagamentoEnum.OUTRO
    assert obj.responsavel == "Jhonatas"
    assert obj.detalhes is None


@pytest.mark.asyncio
async def test_criar_lote_persiste_campos_novos():
    from app.models.enums import FormaPagamentoEnum, StatusEnum

    session = MagicMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TransacaoRepository(session)
    grupo_id = uuid4()
    dtos = [
        make_dto(
            grupo_parcela_id=grupo_id,
            parcela_numero=i + 1,
            status=StatusEnum.PAGO,
            forma_pagamento=FormaPagamentoEnum.CARTAO,
            responsavel="Mãe",
            detalhes="notebook parcelado",
        )
        for i in range(3)
    ]
    await repo.criar_lote(dtos)

    lista_passada = session.add_all.call_args[0][0]
    assert len(lista_passada) == 3
    for obj in lista_passada:
        assert obj.status == StatusEnum.PAGO
        assert obj.forma_pagamento == FormaPagamentoEnum.CARTAO
        assert obj.responsavel == "Mãe"
        assert obj.detalhes == "notebook parcelado"


@pytest.mark.asyncio
async def test_criar_lote_chama_add_all():
    session = MagicMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TransacaoRepository(session)
    grupo_id = uuid4()
    dtos = [make_dto(grupo_parcela_id=grupo_id, parcela_numero=i + 1) for i in range(6)]
    await repo.criar_lote(dtos)

    session.add_all.assert_called_once()
    lista_passada = session.add_all.call_args[0][0]
    assert len(lista_passada) == 6
    assert all(obj.grupo_parcela_id == str(grupo_id) for obj in lista_passada)


@pytest.mark.asyncio
async def test_excluir_grupo_executa_delete_com_grupo_parcela_id():
    grupo_id = uuid4()

    mock_result = MagicMock()
    mock_result.rowcount = 3

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()

    repo = TransacaoRepository(session)
    quantidade = await repo.excluir_grupo(grupo_id)

    session.execute.assert_awaited_once()
    session.flush.assert_awaited_once()
    assert quantidade == 3


@pytest.mark.asyncio
async def test_buscar_por_id_retorna_none_quando_nao_encontrado():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    resultado = await repo.buscar_por_id(999)

    assert resultado is None


@pytest.mark.asyncio
async def test_buscar_semantico_com_distancia_retorna_none_quando_vazio():
    mock_result = MagicMock()
    mock_result.first.return_value = None

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    resultado = await repo.buscar_semantico_com_distancia([0.1] * 1536)

    assert resultado is None


@pytest.mark.asyncio
async def test_agregar_por_categoria_retorna_decimal():
    from app.models.transacao import Transacao

    mock_result = MagicMock()
    mock_result.all.return_value = [
        (CategoriaEnum.ALIMENTACAO, 150.75, 3),
    ]

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    resultado = await repo.agregar_por_categoria(date(2026, 6, 1), date(2026, 6, 30))

    assert len(resultado) == 1
    assert resultado[0].categoria == CategoriaEnum.ALIMENTACAO
    assert isinstance(resultado[0].total, Decimal)
    assert resultado[0].quantidade == 3
