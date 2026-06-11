from datetime import date, timedelta


def test_adicionar_meses_preserva_dia():
    from agent.services.parcelas import adicionar_meses

    assert adicionar_meses(date(2026, 6, 10), 1) == date(2026, 7, 10)
    assert adicionar_meses(date(2026, 6, 10), -1) == date(2026, 5, 10)


def test_adicionar_meses_clampa_ultimo_dia_do_mes():
    from agent.services.parcelas import adicionar_meses

    assert adicionar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_adicionar_meses_clampa_em_ano_bissexto():
    from agent.services.parcelas import adicionar_meses

    assert adicionar_meses(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_adicionar_meses_atravessa_virada_de_ano():
    from agent.services.parcelas import adicionar_meses

    assert adicionar_meses(date(2026, 12, 15), 1) == date(2027, 1, 15)
    assert adicionar_meses(date(2026, 1, 15), -1) == date(2025, 12, 15)


def test_adicionar_meses_zero_retorna_mesma_data():
    from agent.services.parcelas import adicionar_meses

    assert adicionar_meses(date(2026, 6, 10), 0) == date(2026, 6, 10)


def test_status_por_data_passado_pago_futuro_pendente():
    from backend.models.enums import StatusEnum
    from agent.services.parcelas import status_por_data

    hoje = date.today()
    ontem = hoje - timedelta(days=1)
    amanha = hoje + timedelta(days=1)

    assert status_por_data(ontem) == StatusEnum.PAGO
    assert status_por_data(amanha) == StatusEnum.PENDENTE


def test_status_por_data_hoje_e_pendente():
    from backend.models.enums import StatusEnum
    from agent.services.parcelas import status_por_data

    hoje = date(2026, 6, 10)
    assert status_por_data(hoje, hoje=hoje) == StatusEnum.PENDENTE


def test_status_por_data_com_hoje_explicito():
    from backend.models.enums import StatusEnum
    from agent.services.parcelas import status_por_data

    hoje = date(2026, 6, 10)
    assert status_por_data(date(2026, 6, 9), hoje=hoje) == StatusEnum.PAGO
    assert status_por_data(date(2026, 6, 11), hoje=hoje) == StatusEnum.PENDENTE


def test_datas_do_grupo_a_partir_da_parcela_atual():
    from agent.services.parcelas import datas_do_grupo

    resultado = datas_do_grupo(date(2026, 6, 10), parcela_atual=2, parcela_total=4)

    assert resultado == [
        date(2026, 5, 10),
        date(2026, 6, 10),
        date(2026, 7, 10),
        date(2026, 8, 10),
    ]


def test_datas_do_grupo_parcela_unica():
    from agent.services.parcelas import datas_do_grupo

    assert datas_do_grupo(date(2026, 6, 10), 1, 1) == [date(2026, 6, 10)]


def test_datas_do_grupo_primeira_parcela_avanca():
    from agent.services.parcelas import datas_do_grupo

    resultado = datas_do_grupo(date(2026, 1, 31), parcela_atual=1, parcela_total=3)

    assert resultado == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]


def test_enums_novos_existem():
    from backend.models.enums import (
        CategoriaEnum,
        FormaPagamentoEnum,
        StatusEnum,
        TipoEnum,
    )

    assert TipoEnum.RECEITA.value == "RECEITA"
    assert CategoriaEnum.RECEITA.value == "RECEITA"
    assert CategoriaEnum.EDUCACAO.value == "EDUCACAO"
    assert StatusEnum.PAGO.value == "PAGO"
    assert StatusEnum.PENDENTE.value == "PENDENTE"
    assert FormaPagamentoEnum.PIX.value == "PIX"
    assert FormaPagamentoEnum.CARTAO_CREDITO.value == "CARTAO_CREDITO"
    assert FormaPagamentoEnum.CARTAO_DEBITO.value == "CARTAO_DEBITO"
    assert FormaPagamentoEnum.BOLETO.value == "BOLETO"


def test_enums_removidos_nao_existem():
    from backend.models.enums import CategoriaEnum, FormaPagamentoEnum

    assert not hasattr(CategoriaEnum, "PARCELAMENTOS")
    assert not hasattr(CategoriaEnum, "OUTROS")
    assert not hasattr(FormaPagamentoEnum, "OUTRO")
    assert not hasattr(FormaPagamentoEnum, "CARTAO")


def test_transacao_create_defaults_retrocompativeis():
    from decimal import Decimal
    from uuid import uuid4

    from backend.models.enums import (
        CategoriaEnum,
        FormaPagamentoEnum,
        StatusEnum,
        TipoEnum,
    )
    from backend.repositories.dtos import TransacaoCreate

    dto = TransacaoCreate(
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

    assert dto.status == StatusEnum.PENDENTE
    assert dto.forma_pagamento == FormaPagamentoEnum.PIX
    assert dto.recorrente is False
    assert dto.responsavel == "Jhonatas"
    assert dto.detalhes is None


def test_transacao_update_defaults_none():
    from backend.repositories.dtos import TransacaoUpdate

    dto = TransacaoUpdate()

    assert dto.status is None
    assert dto.forma_pagamento is None
    assert dto.recorrente is None
    assert dto.responsavel is None
    assert dto.detalhes is None
