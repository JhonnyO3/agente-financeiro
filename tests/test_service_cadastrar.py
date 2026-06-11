import pytest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from agent.agents.extrator import ExtracaoResult
from backend.models.enums import CategoriaEnum, FormaPagamentoEnum, StatusEnum
from agent.services.cadastrar import CadastrarService
from agent.services.confirmacao_state import ConfirmacaoState, EstadoConfirmacao
from agent.services.parcelas import adicionar_meses


def _cat(valor):
    return SimpleNamespace(categoria=valor)


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
        usuario_id=1,
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
    categorizacao = _cat("ALIMENTACAO")

    transacao_fake = _make_transacao_fake(1, "GASTO", Decimal("45.00"), "mercado", "ALIMENTACAO", hoje, 1, 1, uuid4())
    service, extrator, categorizador, embedder, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=[transacao_fake])

    resultado = await service.executar("gastei 45 no mercado", "5511999999999")

    assert resultado.aguarda_confirmacao is False
    assert len(resultado.transacoes) == 1
    assert resultado.transacoes[0].parcela_total == 1

    categorizador.categorizar.assert_called_once()
    lote_chamado = repository.criar_lote.call_args[0][0]
    assert len(lote_chamado) == 1
    assert lote_chamado[0].valor == Decimal("45.00")
    assert lote_chamado[0].parcela_numero == 1
    assert lote_chamado[0].parcela_total == 1
    assert lote_chamado[0].categoria == CategoriaEnum.ALIMENTACAO
    assert lote_chamado[0].forma_pagamento == FormaPagamentoEnum.PIX
    assert lote_chamado[0].status == StatusEnum.PAGO
    assert lote_chamado[0].recorrente is False
    assert lote_chamado[0].responsavel == "Jhonatas"
    assert lote_chamado[0].detalhes is None
    assert lote_chamado[0].usuario_id == 1


@pytest.mark.asyncio
async def test_forma_nao_informada_assume_pix_pago():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("50.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="almoço",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    service, _, _, _, repository, _ = _make_service(extracao, _cat("ALIMENTACAO"), criar_lote_result=[MagicMock()])

    await service.executar("Gastei 50 no almoço", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].forma_pagamento == FormaPagamentoEnum.PIX
    assert lote[0].status == StatusEnum.PAGO
    assert lote[0].data == hoje


@pytest.mark.asyncio
async def test_parcelas_implicam_cartao_credito_pendente_data_deslocada():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("300.00"),
        valor_por_parcela=Decimal("100.00"),
        parcela_total=3,
        descricao="fone",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    service, _, categorizador, _, repository, _ = _make_service(extracao, _cat("COMPRAS"), criar_lote_result=[MagicMock()] * 3)

    await service.executar("Comprei um fone em 3x de 100", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 3
    for t in lote:
        assert t.forma_pagamento == FormaPagamentoEnum.CARTAO_CREDITO
        assert t.categoria == CategoriaEnum.COMPRAS
        assert t.usuario_id == 1
    assert lote[0].data == adicionar_meses(hoje, 1)
    assert lote[0].status == StatusEnum.PENDENTE
    categorizador.categorizar.assert_called_once()


@pytest.mark.asyncio
async def test_debito_pago_na_hora():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("80.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="mercado",
        data_referencia=hoje,
        menciona_cartao=False,
        forma_pagamento="CARTAO_DEBITO",
    )
    service, _, _, _, repository, _ = _make_service(extracao, _cat("ALIMENTACAO"), criar_lote_result=[MagicMock()])

    await service.executar("Paguei 80 no débito no mercado", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].forma_pagamento == FormaPagamentoEnum.CARTAO_DEBITO
    assert lote[0].status == StatusEnum.PAGO
    assert lote[0].data == hoje


@pytest.mark.asyncio
async def test_boleto_pendente_data_deslocada():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("250.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="conta de luz",
        data_referencia=hoje,
        menciona_cartao=False,
        forma_pagamento="BOLETO",
    )
    service, _, _, _, repository, _ = _make_service(extracao, _cat("GASTOS_PONTUAIS"), criar_lote_result=[MagicMock()])

    await service.executar("conta de luz 250 no boleto", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].forma_pagamento == FormaPagamentoEnum.BOLETO
    assert lote[0].status == StatusEnum.PENDENTE
    assert lote[0].data == adicionar_meses(hoje, 1)


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
    categorizacao = _cat("COMPRAS")

    transacoes_fake = [
        _make_transacao_fake(i + 1, "GASTO", Decimal("150.00"), "celular", "COMPRAS", adicionar_meses(hoje, i + 1), i + 1, 6, uuid4())
        for i in range(6)
    ]
    service, _, categorizador, embedder, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=transacoes_fake)

    resultado = await service.executar("celular 6x de 150", "5511999999999")

    assert resultado.aguarda_confirmacao is False
    assert len(resultado.transacoes) == 6

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 6

    grupo_id = lote[0].grupo_parcela_id
    for i, t in enumerate(lote):
        assert t.grupo_parcela_id == grupo_id
        assert t.parcela_numero == i + 1
        assert t.data == adicionar_meses(hoje, i + 1)
        assert t.categoria == CategoriaEnum.COMPRAS
        assert t.forma_pagamento == FormaPagamentoEnum.CARTAO_CREDITO

    categorizador.categorizar.assert_called_once()
    embedder.gerar_para_transacao.assert_called_once()


@pytest.mark.asyncio
async def test_parcela_atual_gera_grupo_completo_com_passadas():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("800.00"),
        valor_por_parcela=Decimal("200.00"),
        parcela_total=4,
        parcela_atual=2,
        descricao="notebook",
        data_referencia=hoje,
        menciona_cartao=False,
        forma_pagamento="CARTAO_CREDITO",
    )
    categorizacao = _cat("COMPRAS")

    transacoes_fake = [MagicMock() for _ in range(4)]
    service, _, categorizador, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=transacoes_fake)

    resultado = await service.executar("paguei a parcela 2/4 do notebook, 200", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 4

    grupo_id = lote[0].grupo_parcela_id
    data_base = adicionar_meses(hoje, 1)
    datas_esperadas = [adicionar_meses(data_base, i - 1) for i in range(4)]
    for i, t in enumerate(lote):
        assert t.grupo_parcela_id == grupo_id
        assert t.parcela_numero == i + 1
        assert t.data == datas_esperadas[i]
        assert t.valor == Decimal("200.00")
        assert t.categoria == CategoriaEnum.COMPRAS
        assert t.forma_pagamento == FormaPagamentoEnum.CARTAO_CREDITO

    categorizador.categorizar.assert_called_once()
    assert "4 parcelas" in resultado.mensagem_resposta


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
    categorizacao = _cat("COMPRAS")

    transacoes_fake = [MagicMock() for _ in range(6)]
    service, _, _, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=transacoes_fake)

    await service.executar("900 em 6x", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 6
    for t in lote[:-1]:
        assert t.valor == Decimal("150.00")
    assert lote[-1].valor == Decimal("150.00")
    assert sum(t.valor for t in lote) == Decimal("900.00")


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
    categorizacao = _cat("COMPRAS")

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
    categorizacao = _cat("EDUCACAO")

    transacoes_fake = [MagicMock() for _ in range(3)]
    service, _, _, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=transacoes_fake)

    await service.executar("100 em 3x", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 3
    assert lote[0].valor == Decimal("33.33")
    assert lote[1].valor == Decimal("33.33")
    assert lote[2].valor == Decimal("33.34")

    total = sum(t.valor for t in lote)
    assert total == Decimal("100.00")


@pytest.mark.asyncio
async def test_curso_parcelado_categoria_educacao_sem_parcelamentos():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("600.00"),
        valor_por_parcela=None,
        parcela_total=3,
        descricao="curso de inglês",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    service, _, categorizador, _, repository, _ = _make_service(extracao, _cat("EDUCACAO"), criar_lote_result=[MagicMock()] * 3)

    await service.executar("curso de inglês 600 em 3x", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    for t in lote:
        assert t.categoria == CategoriaEnum.EDUCACAO
        assert t.tipo == "GASTO"
    categorizador.categorizar.assert_called_once()


@pytest.mark.asyncio
async def test_pix_a_vista_nasce_pago():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("80.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="jantar",
        data_referencia=hoje,
        menciona_cartao=False,
        forma_pagamento="PIX",
    )
    categorizacao = _cat("ALIMENTACAO")

    service, _, _, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=[MagicMock()])

    await service.executar("paguei 80 no pix do jantar", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 1
    assert lote[0].status == StatusEnum.PAGO
    assert lote[0].forma_pagamento == FormaPagamentoEnum.PIX


@pytest.mark.asyncio
async def test_receita_forca_categoria_e_status_sem_categorizador():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="RECEITA",
        valor_total=Decimal("5000.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="salário",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    categorizacao = _cat("ALIMENTACAO")

    service, _, categorizador, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=[MagicMock()])

    await service.executar("recebi salário 5000", "5511999999999")

    categorizador.categorizar.assert_not_called()
    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 1
    assert lote[0].categoria == CategoriaEnum.RECEITA
    assert lote[0].status == StatusEnum.PAGO


@pytest.mark.asyncio
async def test_receita_futura_fica_pendente():
    hoje = date.today()
    futuro = adicionar_meses(hoje, 1)
    extracao = ExtracaoResult(
        tipo="RECEITA",
        valor_total=Decimal("1000.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="freela",
        data_referencia=futuro,
        menciona_cartao=False,
    )
    categorizacao = _cat("ALIMENTACAO")

    service, _, categorizador, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=[MagicMock()])

    await service.executar("vou receber 1000 mês que vem", "5511999999999")

    categorizador.categorizar.assert_not_called()
    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].categoria == CategoriaEnum.RECEITA
    assert lote[0].status == StatusEnum.PENDENTE


@pytest.mark.asyncio
async def test_responsavel_e_detalhes_propagados():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("120.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="jogo",
        detalhes="promoção da Steam",
        data_referencia=hoje,
        menciona_cartao=False,
        responsavel="Mãe",
    )
    categorizacao = _cat("LAZER")

    service, _, _, _, repository, _ = _make_service(extracao, categorizacao, criar_lote_result=[MagicMock()])

    await service.executar("minha mãe comprou um jogo na promoção da Steam", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].responsavel == "Mãe"
    assert lote[0].detalhes == "promoção da Steam"


@pytest.mark.asyncio
async def test_executar_com_parcelas_confirmadas_continua_funcionando():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("300.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="tênis",
        data_referencia=hoje,
        menciona_cartao=True,
        forma_pagamento="CARTAO_CREDITO",
    )
    categorizacao = _cat("COMPRAS")

    transacoes_fake = [MagicMock() for _ in range(3)]
    service, _, categorizador, _, repository, confirmacao_state = _make_service(extracao, categorizacao, criar_lote_result=transacoes_fake)
    confirmacao_state.salvar(
        "5511999999999",
        EstadoConfirmacao(acao="AGUARDAR_PARCELAS", mensagem_original="comprei tênis 300 no cartão"),
    )

    resultado = await service.executar_com_parcelas_confirmadas("comprei tênis 300 no cartão", 3, "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 3
    assert sum(t.valor for t in lote) == Decimal("300.00")
    data_base = adicionar_meses(hoje, 1)
    for i, t in enumerate(lote):
        assert t.parcela_numero == i + 1
        assert t.data == adicionar_meses(data_base, i)
        assert t.categoria == CategoriaEnum.COMPRAS
        assert t.forma_pagamento == FormaPagamentoEnum.CARTAO_CREDITO
    assert confirmacao_state.obter("5511999999999") is None
    assert resultado.aguarda_confirmacao is False


@pytest.mark.asyncio
async def test_gastos_fixos_dispara_pergunta_recorrencia():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("99.90"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="academia",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    service, _, _, _, repository, confirmacao_state = _make_service(extracao, _cat("GASTOS_FIXOS"))

    resultado = await service.executar("paguei a academia 99,90", "5511999999999")

    assert resultado.aguarda_confirmacao is True
    assert resultado.pergunta is not None
    repository.criar_lote.assert_not_called()
    estado = confirmacao_state.obter("5511999999999")
    assert estado is not None
    assert estado.acao == "AGUARDAR_RECORRENCIA"
    assert estado.mensagem_original == "paguei a academia 99,90"


@pytest.mark.asyncio
async def test_recorrencia_confirmada_grava_recorrente_true_sem_parcela():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("99.90"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="academia",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    service, _, _, _, repository, confirmacao_state = _make_service(extracao, _cat("GASTOS_FIXOS"), criar_lote_result=[MagicMock()])
    confirmacao_state.salvar(
        "5511999999999",
        EstadoConfirmacao(acao="AGUARDAR_RECORRENCIA", mensagem_original="paguei a academia 99,90"),
    )

    await service.executar_com_recorrencia_confirmada("paguei a academia 99,90", True, "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 1
    assert lote[0].recorrente is True
    assert lote[0].parcela_numero == 1
    assert lote[0].parcela_total == 1
    assert lote[0].categoria == CategoriaEnum.GASTOS_FIXOS
    assert confirmacao_state.obter("5511999999999") is None


@pytest.mark.asyncio
async def test_recorrencia_negada_grava_recorrente_false():
    hoje = date.today()
    extracao = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("99.90"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="academia",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    service, _, _, _, repository, confirmacao_state = _make_service(extracao, _cat("GASTOS_FIXOS"), criar_lote_result=[MagicMock()])
    confirmacao_state.salvar(
        "5511999999999",
        EstadoConfirmacao(acao="AGUARDAR_RECORRENCIA", mensagem_original="paguei a academia 99,90"),
    )

    await service.executar_com_recorrencia_confirmada("paguei a academia 99,90", False, "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].recorrente is False
    assert lote[0].parcela_total == 1


@pytest.mark.asyncio
async def test_executar_lote_gera_grupo_completo_com_status():
    from agent.agents.extrator_lista import ExtracaoListaResult, ItemLista

    hoje = date.today()
    extracao_lista = ExtracaoListaResult(
        itens=[
            ItemLista(
                descricao="LinkedIn",
                valor=Decimal("49.33"),
                parcela_numero=2,
                parcela_total=3,
                data=hoje,
                tipo="GASTO",
                categoria="GASTOS_FIXOS",
            ),
            ItemLista(
                descricao="mercado",
                valor=Decimal("100.00"),
                data=adicionar_meses(hoje, -1),
                tipo="GASTO",
                categoria="ALIMENTACAO",
            ),
        ]
    )
    extrator_lista = MagicMock()
    extrator_lista.extrair = AsyncMock(return_value=extracao_lista)

    service, _, _, _, repository, _ = _make_service(None, None, criar_lote_result=[MagicMock()] * 4)

    resultado = await service.executar_lote("lista de contas", extrator_lista)

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 4

    parcelas_linkedin = lote[:3]
    grupo_id = parcelas_linkedin[0].grupo_parcela_id
    for i, t in enumerate(parcelas_linkedin):
        assert t.grupo_parcela_id == grupo_id
        assert t.parcela_numero == i + 1
        assert t.parcela_total == 3
        assert t.valor == Decimal("49.33")
        assert t.data == adicionar_meses(hoje, i - 1)
        assert t.categoria == CategoriaEnum.GASTOS_FIXOS
    assert parcelas_linkedin[0].status == StatusEnum.PAGO
    assert parcelas_linkedin[1].status == StatusEnum.PENDENTE
    assert parcelas_linkedin[2].status == StatusEnum.PENDENTE

    assert all(t.usuario_id == 1 for t in lote)

    mercado = lote[3]
    assert mercado.parcela_total == 1
    assert mercado.categoria == CategoriaEnum.ALIMENTACAO
    assert mercado.status == StatusEnum.PAGO
    assert mercado.grupo_parcela_id != grupo_id


@pytest.mark.asyncio
async def test_executar_lote_receitas_categoria_receita_e_pago():
    from agent.agents.extrator_lista import ExtracaoListaResult, ItemLista

    hoje = date.today()
    extracao_lista = ExtracaoListaResult(
        itens=[
            ItemLista(
                descricao="salário do bradesco",
                valor=Decimal("7463.00"),
                data=hoje,
                tipo="RECEITA",
                categoria="RECEITA",
            ),
            ItemLista(
                descricao="décimo terceiro",
                valor=Decimal("4644.00"),
                data=hoje,
                tipo="RECEITA",
                categoria="GASTOS_PONTUAIS",
            ),
        ]
    )
    extrator_lista = MagicMock()
    extrator_lista.extrair = AsyncMock(return_value=extracao_lista)

    service, _, _, _, repository, _ = _make_service(None, None, criar_lote_result=[MagicMock()] * 2)

    await service.executar_lote("recebi salário e 13º", extrator_lista)

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 2
    for t in lote:
        assert t.tipo == "RECEITA"
        assert t.categoria == CategoriaEnum.RECEITA
        assert t.status == StatusEnum.PAGO


@pytest.mark.asyncio
async def test_mensagem_resposta_simples_e_parcelada():
    hoje = date.today()
    extracao_simples = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("45.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="mercado",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    categorizacao = _cat("ALIMENTACAO")
    service, _, _, _, _, _ = _make_service(extracao_simples, categorizacao, criar_lote_result=[MagicMock()])

    resultado = await service.executar("gastei 45 no mercado", "5511999999999")
    assert "mercado" in resultado.mensagem_resposta
    assert "45.00" in resultado.mensagem_resposta

    extracao_parcelada = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("600.00"),
        valor_por_parcela=None,
        parcela_total=3,
        descricao="cadeira",
        data_referencia=hoje,
        menciona_cartao=False,
    )
    service2, _, _, _, _, _ = _make_service(extracao_parcelada, categorizacao, criar_lote_result=[MagicMock()] * 3)

    resultado2 = await service2.executar("cadeira 600 em 3x", "5511999999999")
    assert "3 parcelas" in resultado2.mensagem_resposta
    assert "já paga" not in resultado2.mensagem_resposta
