import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# Variáveis de ambiente obrigatórias ANTES de qualquer import que carregue Settings
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake-key-for-tests")
os.environ.setdefault("EVOLUTION_API_URL", "http://fake-evolution")
os.environ.setdefault("EVOLUTION_INSTANCE", "fake-instance")
os.environ.setdefault("EVOLUTION_API_KEY", "fake-api-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511999999999")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Jhon")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "test@exemplo.com")
os.environ.setdefault("WEBHOOK_APIKEY", "test-apikey")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest

from agent.domain.intencao import (
    Intencao,
    ItemCadastro,
    ParamsCadastrar,
    ParamsComplementar,
    ParamsExcluir,
    ParamsListar,
    ParamsAtualizar,
    ParamsSelecionar,
    ParamsVazio,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _intencao(acao: str, parametros: dict, confianca: float) -> Intencao:
    return Intencao.model_validate({"acao": acao, "parametros": parametros, "confianca": confianca})


def _make_chain_mock(intencao: Intencao) -> MagicMock:
    """Retorna um mock de chain com ainvoke que devolve a Intencao fornecida."""
    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=intencao)
    return chain


# ---------------------------------------------------------------------------
# Cenário principal: exemplos da tabela de classificador.md
# Os 17 exemplos da tabela viram casos parametrizados.
# O mock do LLM devolve a Intencao esperada; verificamos que o classificador
# repassa essa Intencao sem mutação.
# ---------------------------------------------------------------------------

EXEMPLOS = [
    (
        "gastei_472_claude_code",
        "Gastei 472 reais com Claude code",
        "nenhuma",
        _intencao("cadastrar", {"itens": [{"descricao": "Claude Code", "valor": 472}]}, 0.98),
    ),
    (
        "140_flores_190_internet",
        "140 das flores e 190 de internet ontem",
        "nenhuma",
        _intencao(
            "cadastrar",
            {
                "itens": [
                    {"descricao": "Flores", "valor": 140},
                    {"descricao": "Internet", "valor": 190, "data": "ontem"},
                ]
            },
            0.96,
        ),
    ),
    (
        "listar_gastos",
        "listar gastos",
        "nenhuma",
        _intencao("listar", {"periodo": "mes_atual"}, 0.99),
    ),
    (
        "quanto_gastei_esse_mes",
        "quanto gastei esse mês?",
        "nenhuma",
        _intencao("listar", {"periodo": "mes_atual"}, 0.97),
    ),
    (
        "estou_no_azul",
        "estou no azul esse mês?",
        "nenhuma",
        _intencao("listar", {"periodo": "mes_atual"}, 0.92),
    ),
    (
        "vale_a_pena_parcelar",
        "vale a pena parcelar uma compra grande?",
        "nenhuma",
        _intencao("conversar", {}, 0.93),
    ),
    (
        "corrige_valor_zara",
        "corrige o valor da zara para 200",
        "nenhuma",
        _intencao("atualizar", {"referencia": "zara", "campo": "valor", "novo_valor": "200"}, 0.96),
    ),
    (
        "paguei_a_internet",
        "paguei a internet",
        "nenhuma",
        _intencao("atualizar", {"referencia": "internet", "campo": "status", "novo_valor": "PAGO"}, 0.94),
    ),
    (
        "apaga_gasto_flores",
        "apaga o gasto das flores",
        "nenhuma",
        _intencao("excluir", {"referencia": "flores"}, 0.95),
    ),
    (
        "apaga_tudo_de_maio",
        "apaga tudo de maio",
        "nenhuma",
        _intencao("excluir", {"periodo": "2026-05"}, 0.95),
    ),
    (
        "confirmar",
        "confirmar",
        "cadastro aguardando confirmação",
        _intencao("confirmar", {}, 0.99),
    ),
    (
        "nao_deixa_cancelar",
        "não, deixa",
        "exclusão aguardando confirmação",
        _intencao("cancelar", {}, 0.98),
    ),
    (
        "selecionar_opcao_2",
        "2",
        "lista de 3 opções exibida",
        _intencao("selecionar", {"opcao": 2}, 0.99),
    ),
    (
        "todos_selecionar_opcao_2",
        "todos",
        "exclusão aguardando escopo",
        _intencao("selecionar", {"opcao": 2}, 0.97),
    ),
    (
        "foi_350_complementar_valor",
        "foi 350",
        "cadastro aguardando valor",
        _intencao("complementar", {"campo": "valor", "valor": "350"}, 0.97),
    ),
    (
        "em_3x_complementar_parcelas",
        "em 3x",
        "cadastro aguardando parcelas",
        _intencao("complementar", {"campo": "parcelas", "valor": "3"}, 0.97),
    ),
    (
        "me_conta_uma_piada_desconhecida",
        "me conta uma piada",
        "nenhuma",
        _intencao("desconhecida", {}, 0.99),
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exemplo_id,mensagem,estado_pendente,intencao_esperada",
    EXEMPLOS,
    ids=[e[0] for e in EXEMPLOS],
)
async def test_classificador_exemplos_tabela(
    exemplo_id, mensagem, estado_pendente, intencao_esperada
):
    """Mock do LLM devolvendo cada exemplo da tabela → classificador repassa a Intencao correta."""
    from agent.services.classificador import Classificador

    chain_mock = _make_chain_mock(intencao_esperada)
    llm_mock = MagicMock()
    llm_mock.with_structured_output = MagicMock(return_value=chain_mock)

    with patch("agent.services.classificador.criar_llm", return_value=llm_mock):
        classificador = Classificador()
        resultado = await classificador.classificar(
            mensagem=mensagem,
            historico=[],
            estado_pendente=estado_pendente,
        )

    assert resultado.acao == intencao_esperada.acao, (
        f"[{exemplo_id}] esperava acao={intencao_esperada.acao!r}, obteve {resultado.acao!r}"
    )


# ---------------------------------------------------------------------------
# Cenário: confianca < CONFIANCA_MINIMA → acao vira "desconhecida"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_confianca_baixa_vira_desconhecida():
    """LLM devolve confianca=0.5 com acao='cadastrar'; serviço deve retornar 'desconhecida'."""
    from agent.services.classificador import Classificador

    intencao_llm = _intencao("cadastrar", {"itens": []}, 0.5)
    chain_mock = _make_chain_mock(intencao_llm)
    llm_mock = MagicMock()
    llm_mock.with_structured_output = MagicMock(return_value=chain_mock)

    with patch("agent.services.classificador.criar_llm", return_value=llm_mock):
        with patch("agent.services.classificador.settings") as mock_settings:
            mock_settings.CONFIANCA_MINIMA = 0.7
            mock_settings.RESPONSAVEL_PADRAO = "Jhon"
            classificador = Classificador()
            resultado = await classificador.classificar(
                mensagem="mensagem ambígua",
                historico=[],
                estado_pendente="nenhuma",
            )

    assert resultado.acao == "desconhecida", (
        f"Esperava 'desconhecida', obteve {resultado.acao!r}"
    )


# ---------------------------------------------------------------------------
# Cenário: historico e estado_pendente são injetados no contexto do prompt
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_historico_e_estado_pendente_injetados_no_prompt():
    """O classificador deve repassar historico e estado_pendente ao montar_prompt."""
    from agent.services.classificador import Classificador

    intencao_retorno = _intencao("confirmar", {}, 0.99)
    chain_mock = _make_chain_mock(intencao_retorno)
    llm_mock = MagicMock()
    llm_mock.with_structured_output = MagicMock(return_value=chain_mock)

    historico = ["Usuário: gastei 100 no uber", "Agente: Registrado!"]
    estado = "cadastro aguardando confirmação"

    captured_ctx: dict = {}

    def montar_prompt_spy(acao: str, contexto: dict) -> str:
        captured_ctx.update(contexto)
        return "prompt_fake"

    with patch("agent.services.classificador.criar_llm", return_value=llm_mock):
        with patch("agent.services.classificador.montar_prompt", side_effect=montar_prompt_spy):
            classificador = Classificador()
            await classificador.classificar(
                mensagem="confirmar",
                historico=historico,
                estado_pendente=estado,
            )

    # O contexto passado a montar_prompt deve conter o estado_pendente
    assert "estado_pendente" in captured_ctx, (
        "estado_pendente não foi passado ao montar_prompt"
    )
    assert captured_ctx["estado_pendente"] == estado, (
        f"estado_pendente errado: {captured_ctx['estado_pendente']!r}"
    )

    # E o histórico deve estar representado no contexto (como string ou lista)
    assert "historico_recente" in captured_ctx, (
        "historico_recente não foi passado ao montar_prompt"
    )

    historico_val = captured_ctx["historico_recente"]
    # Verifica que o conteúdo do histórico aparece na representação
    assert any(
        "uber" in str(historico_val).lower() or "registrado" in str(historico_val).lower()
        for _ in [1]
    ), f"Conteúdo do histórico não aparece em historico_recente: {historico_val!r}"


# ---------------------------------------------------------------------------
# Cenário: estado_pendente injetado como variável "estado_pendente" no contexto
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estado_pendente_presente_no_contexto_do_prompt():
    """estado_pendente deve aparecer no contexto passado a montar_prompt."""
    from agent.services.classificador import Classificador

    intencao_retorno = _intencao("cadastrar", {"itens": []}, 0.95)
    chain_mock = _make_chain_mock(intencao_retorno)
    llm_mock = MagicMock()
    llm_mock.with_structured_output = MagicMock(return_value=chain_mock)

    estado = "exclusão aguardando confirmação"
    captured_ctx: dict = {}

    def montar_prompt_spy(acao: str, contexto: dict) -> str:
        captured_ctx.update(contexto)
        return "prompt_fake"

    with patch("agent.services.classificador.criar_llm", return_value=llm_mock):
        with patch("agent.services.classificador.montar_prompt", side_effect=montar_prompt_spy):
            classificador = Classificador()
            await classificador.classificar(
                mensagem="gastei 30 no uber",
                historico=[],
                estado_pendente=estado,
            )

    assert captured_ctx.get("estado_pendente") == estado


# ---------------------------------------------------------------------------
# Cenário: prompt montado via montar_prompt("classificador", ctx)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_montado_com_acao_classificador():
    """Verificar que montar_prompt é chamado com acao='classificador'."""
    from agent.services.classificador import Classificador

    intencao_retorno = _intencao("listar", {"periodo": "mes_atual"}, 0.99)
    chain_mock = _make_chain_mock(intencao_retorno)
    llm_mock = MagicMock()
    llm_mock.with_structured_output = MagicMock(return_value=chain_mock)

    chamadas: list = []

    def montar_prompt_spy(acao: str, contexto: dict) -> str:
        chamadas.append({"acao": acao, "contexto": contexto})
        return "prompt_fake"

    with patch("agent.services.classificador.criar_llm", return_value=llm_mock):
        with patch("agent.services.classificador.montar_prompt", side_effect=montar_prompt_spy):
            classificador = Classificador()
            await classificador.classificar(
                mensagem="listar gastos",
                historico=[],
                estado_pendente="nenhuma",
            )

    assert len(chamadas) >= 1, "montar_prompt não foi chamado"
    assert chamadas[0]["acao"] == "classificador", (
        f"montar_prompt chamado com acao={chamadas[0]['acao']!r}, esperava 'classificador'"
    )


# ---------------------------------------------------------------------------
# Cenário: intenção nova durante pendência não força confirmar
# (mock devolve "cadastrar" mesmo com estado_pendente de exclusão)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_intencao_nova_durante_pendencia_nao_forca_confirmar():
    """LLM devolve 'cadastrar' para 'gastei 30 no uber' mesmo com pendência de exclusão."""
    from agent.services.classificador import Classificador

    intencao_llm = _intencao(
        "cadastrar",
        {"itens": [{"descricao": "Uber", "valor": 30}]},
        0.95,
    )
    chain_mock = _make_chain_mock(intencao_llm)
    llm_mock = MagicMock()
    llm_mock.with_structured_output = MagicMock(return_value=chain_mock)

    with patch("agent.services.classificador.criar_llm", return_value=llm_mock):
        classificador = Classificador()
        resultado = await classificador.classificar(
            mensagem="gastei 30 no uber",
            historico=[],
            estado_pendente="exclusão aguardando confirmação",
        )

    assert resultado.acao == "cadastrar"
    assert isinstance(resultado.parametros, ParamsCadastrar)
    assert len(resultado.parametros.itens) == 1
    item = resultado.parametros.itens[0]
    assert "uber" in (item.descricao or "").lower()
    assert item.valor == Decimal("30")


# ---------------------------------------------------------------------------
# Cenário: estado_pendente "nenhuma" — mock devolve "confirmar" mas
# o serviço deve converter para "desconhecida" (regra do contrato)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_estado_nenhuma_nao_permite_confirmar():
    """Quando estado_pendente='nenhuma', acao 'confirmar' deve virar 'desconhecida'."""
    from agent.services.classificador import Classificador

    # LLM tenta devolver "confirmar" com confianca alta
    intencao_llm = _intencao("confirmar", {}, 0.8)
    chain_mock = _make_chain_mock(intencao_llm)
    llm_mock = MagicMock()
    llm_mock.with_structured_output = MagicMock(return_value=chain_mock)

    with patch("agent.services.classificador.criar_llm", return_value=llm_mock):
        classificador = Classificador()
        resultado = await classificador.classificar(
            mensagem="sim",
            historico=[],
            estado_pendente="nenhuma",
        )

    assert resultado.acao != "confirmar", (
        "Com estado_pendente='nenhuma', acao 'confirmar' não deve ser permitida"
    )


# ---------------------------------------------------------------------------
# Cenário: Classificador é importável e instanciável
# ---------------------------------------------------------------------------

def test_classificador_importavel():
    """Importação de Classificador deve funcionar sem erro."""
    from agent.services.classificador import Classificador  # noqa

    assert callable(Classificador)


@pytest.mark.asyncio
async def test_classificador_tem_metodo_classificar():
    """Classificador deve expor método async classificar."""
    from agent.services.classificador import Classificador
    import inspect

    assert hasattr(Classificador, "classificar"), "método classificar não existe"
    assert inspect.iscoroutinefunction(Classificador.classificar), (
        "classificar deve ser async"
    )


# ---------------------------------------------------------------------------
# Cenário: chain criada com with_structured_output(Intencao)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chain_usa_structured_output_intencao():
    """Verificar que with_structured_output é chamado com a classe Intencao."""
    from agent.services.classificador import Classificador

    intencao_retorno = _intencao("listar", {"periodo": "mes_atual"}, 0.99)
    chain_mock = _make_chain_mock(intencao_retorno)
    llm_mock = MagicMock()
    llm_mock.with_structured_output = MagicMock(return_value=chain_mock)

    with patch("agent.services.classificador.criar_llm", return_value=llm_mock):
        with patch("agent.services.classificador.montar_prompt", return_value="prompt_fake"):
            classificador = Classificador()
            await classificador.classificar(
                mensagem="listar gastos",
                historico=[],
                estado_pendente="nenhuma",
            )

    llm_mock.with_structured_output.assert_called_once_with(Intencao)
