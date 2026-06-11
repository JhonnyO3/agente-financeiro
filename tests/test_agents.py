import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_classificador_cadastrar():
    from app.agents.classificador import Classificador, IntencaoResult

    resultado = IntencaoResult(intencao="CADASTRAR", confianca="alta")

    with patch("app.agents.classificador.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        classificador = Classificador()
        resp = await classificador.classificar("gastei 50 no mercado")

    assert resp.intencao == "CADASTRAR"
    assert resp.confianca == "alta"


@pytest.mark.asyncio
async def test_categorizador_investimento_sem_llm():
    from app.agents.categorizador import Categorizador, CategorizacaoResult

    with patch("app.agents.categorizador.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock()
        mock_criar.return_value = mock_chain

        categorizador = Categorizador()
        resp = await categorizador.categorizar("INVESTIMENTO", "PETR4", 300.0)

    assert resp.categoria == "INVESTIMENTO"
    mock_chain.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_categorizador_curso_vira_educacao():
    from app.agents.categorizador import Categorizador, CategorizacaoResult

    resultado = CategorizacaoResult(categoria="EDUCACAO")

    with patch("app.agents.categorizador.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        categorizador = Categorizador()
        resp = await categorizador.categorizar("GASTO", "curso de inglês", 1200.0)

    assert resp.categoria == "EDUCACAO"
    mock_chain.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_categorizador_objeto_vira_compras():
    from app.agents.categorizador import Categorizador, CategorizacaoResult

    resultado = CategorizacaoResult(categoria="COMPRAS")

    with patch("app.agents.categorizador.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        categorizador = Categorizador()
        resp = await categorizador.categorizar("GASTO", "console", 2400.0)

    assert resp.categoria == "COMPRAS"


def test_categorizacao_result_literal_sem_outros():
    from app.agents.categorizador import CategorizacaoResult

    args = CategorizacaoResult.model_fields["categoria"].annotation.__args__
    assert set(args) == {
        "ALIMENTACAO",
        "TRANSPORTE",
        "LAZER",
        "EDUCACAO",
        "GASTOS_FIXOS",
        "COMPRAS",
        "GASTOS_PONTUAIS",
    }
    assert "OUTROS" not in args
    assert "PARCELAMENTOS" not in args


def test_extracao_result_retrocompatibilidade_defaults():
    from app.agents.extrator import ExtracaoResult

    dados_antigos = {
        "tipo": "GASTO",
        "valor_total": Decimal("50"),
        "valor_por_parcela": None,
        "parcela_total": 1,
        "descricao": "mercado",
        "data_referencia": date(2026, 6, 10),
        "menciona_cartao": False,
    }

    resultado = ExtracaoResult(**dados_antigos)

    assert resultado.parcela_atual == 1
    assert resultado.forma_pagamento == "PIX"
    assert resultado.responsavel == "Jhonatas"
    assert resultado.detalhes is None


def test_extracao_result_parcela_atual_e_valor_por_parcela():
    from app.agents.extrator import ExtracaoResult

    resultado = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("800"),
        valor_por_parcela=Decimal("200"),
        parcela_total=4,
        parcela_atual=2,
        descricao="notebook",
        data_referencia=date(2026, 6, 10),
        menciona_cartao=True,
        forma_pagamento="CARTAO_CREDITO",
    )

    assert resultado.valor_por_parcela == Decimal("200")
    assert resultado.parcela_total == 4
    assert resultado.parcela_atual == 2
    assert resultado.valor_total == Decimal("800")


def test_extracao_result_aceita_tipo_receita():
    from app.agents.extrator import ExtracaoResult

    resultado = ExtracaoResult(
        tipo="RECEITA",
        valor_total=Decimal("5000"),
        valor_por_parcela=None,
        descricao="salário",
        data_referencia=date(2026, 6, 5),
        menciona_cartao=False,
    )

    assert resultado.tipo == "RECEITA"


def test_extracao_result_campos_novos_preenchidos():
    from app.agents.extrator import ExtracaoResult

    resultado = ExtracaoResult(
        tipo="GASTO",
        valor_total=Decimal("120"),
        valor_por_parcela=None,
        descricao="farmácia",
        detalhes="remédio para a mãe, comprado na volta do trabalho",
        data_referencia=date(2026, 6, 10),
        menciona_cartao=False,
        forma_pagamento="PIX",
        responsavel="Mãe",
    )

    assert resultado.forma_pagamento == "PIX"
    assert resultado.responsavel == "Mãe"
    assert resultado.detalhes == "remédio para a mãe, comprado na volta do trabalho"


@pytest.mark.asyncio
async def test_extrator_extrair_retorna_campos_v2():
    from app.agents.extrator import Extrator, ExtracaoResult

    resultado = ExtracaoResult(
        tipo="RECEITA",
        valor_total=Decimal("5000"),
        valor_por_parcela=None,
        descricao="salário",
        data_referencia=date(2026, 6, 5),
        menciona_cartao=False,
        forma_pagamento="PIX",
    )

    with patch("app.agents.extrator.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        extrator = Extrator()
        resp = await extrator.extrair("recebi salário 5000 no pix", date(2026, 6, 10))

    assert resp.tipo == "RECEITA"
    assert resp.forma_pagamento == "PIX"
    assert resp.parcela_atual == 1
    assert resp.responsavel == "Jhonatas"
    assert resp.detalhes is None


@pytest.mark.asyncio
async def test_extrator_parcelas_a_vista():
    from app.agents.extrator_parcelas import ExtratorParcelas, ExtratorParcelasResult

    resultado = ExtratorParcelasResult(parcela_total=1)

    with patch("app.agents.extrator_parcelas.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        extrator = ExtratorParcelas()
        resp = await extrator.extrair("à vista")

    assert resp.parcela_total == 1


@pytest.mark.asyncio
async def test_extrator_parcelas_tres_vezes():
    from app.agents.extrator_parcelas import ExtratorParcelas, ExtratorParcelasResult

    resultado = ExtratorParcelasResult(parcela_total=3)

    with patch("app.agents.extrator_parcelas.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        extrator = ExtratorParcelas()
        resp = await extrator.extrair("3 vezes")

    assert resp.parcela_total == 3


@pytest.mark.asyncio
async def test_extrator_alteracao_novo_valor():
    from app.agents.extrator_alteracao import ExtratorAlteracao, ExtracaoAlteracaoResult

    resultado = ExtracaoAlteracaoResult(novo_valor=Decimal("80"))

    with patch("app.agents.extrator_alteracao.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        extrator = ExtratorAlteracao()
        resp = await extrator.extrair("muda para 80 reais", date.today())

    assert resp.novo_valor == Decimal("80")
    assert resp.nova_descricao is None
    assert resp.nova_categoria is None
    assert resp.nova_data is None


@pytest.mark.asyncio
async def test_filtro_consulta_mensal():
    from app.agents.filtro_consulta import FiltroConsulta, FiltroConsultaResult

    resultado = FiltroConsultaResult(tipo_consulta="mensal", mes=6, ano=2026)

    with patch("app.agents.filtro_consulta.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        filtro = FiltroConsulta()
        resp = await filtro.extrair("resumo de junho", date(2026, 6, 9))

    assert resp.tipo_consulta == "mensal"
    assert resp.mes == 6


@pytest.mark.asyncio
async def test_confirmacao_sim_nao():
    from app.agents.confirmacao_chain import ConfirmacaoChain, ConfirmacaoResposta

    resultado = ConfirmacaoResposta(tipo="sim")

    with patch("app.agents.confirmacao_chain.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        chain = ConfirmacaoChain()
        resp = await chain.interpretar("pode ser", "sim_nao")

    assert resp.tipo == "sim"


@pytest.mark.asyncio
async def test_confirmacao_escopo_parcela():
    from app.agents.confirmacao_chain import ConfirmacaoChain, ConfirmacaoResposta

    resultado = ConfirmacaoResposta(tipo="parcela")

    with patch("app.agents.confirmacao_chain.criar_llm") as mock_criar:
        mock_chain = MagicMock()
        mock_chain.with_structured_output.return_value = mock_chain
        mock_chain.ainvoke = AsyncMock(return_value=resultado)
        mock_criar.return_value = mock_chain

        chain = ConfirmacaoChain()
        resp = await chain.interpretar("só essa", "escopo_parcela")

    assert resp.tipo == "parcela"


@pytest.mark.asyncio
async def test_embedder_gerar_para_transacao():
    from app.agents.embedder import Embedder

    vetor_fake = [0.1] * 1536

    with patch("app.agents.embedder.OpenAIEmbeddings") as mock_emb_cls:
        mock_client = MagicMock()
        mock_client.aembed_query = AsyncMock(return_value=vetor_fake)
        mock_emb_cls.return_value = mock_client

        embedder = Embedder()
        result = await embedder.gerar_para_transacao(
            "GASTO", "ALIMENTACAO", "mercado", date(2026, 6, 12)
        )

    assert result == vetor_fake
    mock_client.aembed_query.assert_called_once_with(
        "GASTO ALIMENTACAO mercado 12/06/2026"
    )


@pytest.mark.asyncio
async def test_embedder_gerar_para_transacao_sem_descricao():
    from app.agents.embedder import Embedder

    vetor_fake = [0.2] * 1536

    with patch("app.agents.embedder.OpenAIEmbeddings") as mock_emb_cls:
        mock_client = MagicMock()
        mock_client.aembed_query = AsyncMock(return_value=vetor_fake)
        mock_emb_cls.return_value = mock_client

        embedder = Embedder()
        result = await embedder.gerar_para_transacao(
            "INVESTIMENTO", "INVESTIMENTO", None, date(2026, 6, 9)
        )

    assert result == vetor_fake
    mock_client.aembed_query.assert_called_once_with(
        "INVESTIMENTO INVESTIMENTO 09/06/2026"
    )


def test_coagir_data_aceita_iso_e_ddmmyyyy():
    from datetime import date

    from app.agents.base import coagir_data

    assert coagir_data("2026-06-10") == date(2026, 6, 10)
    assert coagir_data("10/06/2026") == date(2026, 6, 10)
    assert coagir_data(date(2026, 6, 10)) == date(2026, 6, 10)
    assert coagir_data(None) is None


def test_extracao_result_aceita_data_ddmmyyyy():
    from datetime import date

    from app.agents.extrator import ExtracaoResult

    resultado = ExtracaoResult(
        tipo="INVESTIMENTO",
        valor_total=Decimal("3202"),
        valor_por_parcela=None,
        descricao="bitcoin",
        data_referencia="10/06/2026",
        menciona_cartao=False,
    )
    assert resultado.data_referencia == date(2026, 6, 10)
