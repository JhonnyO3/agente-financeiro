import os

# Vars de ambiente obrigatórias antes de qualquer import que carregue Settings
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
from unittest.mock import AsyncMock, MagicMock, patch, call


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _mock_repository():
    """Repository mockado sem nenhuma chamada esperada."""
    repo = MagicMock()
    # Garante que qualquer chamada assíncrona também seja rastreável
    repo.buscar = AsyncMock()
    repo.salvar = AsyncMock()
    repo.listar = AsyncMock()
    repo.excluir = AsyncMock()
    return repo


def _mock_llm(resposta: str = "Resposta mock do LLM"):
    """LLM mockado com ainvoke retornando AIMessage-like com content."""
    llm = MagicMock()
    ai_message = MagicMock()
    ai_message.content = resposta
    llm.ainvoke = AsyncMock(return_value=ai_message)
    return llm


# ---------------------------------------------------------------------------
# Cenário 1: executar retorna ResultadoTool com acao="conversar", status="concluido"
#             e dados={"resposta": <texto do LLM>}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_executar_retorna_resultado_tool_conversar():
    """Caminho feliz: resposta do LLM vai para dados.resposta."""
    llm = _mock_llm("Vale sim, depende do CET")
    repo = _mock_repository()

    with patch("agent.tools.conversar.criar_llm", return_value=llm):
        from agent.tools.conversar import ToolConversar
        tool = ToolConversar(repository=repo)
        resultado = await tool.executar(
            mensagem="vale a pena parcelar uma compra grande?",
            historico=[],
        )

    assert resultado.acao == "conversar"
    assert resultado.status == "concluido"
    assert resultado.dados["resposta"] == "Vale sim, depende do CET"


# ---------------------------------------------------------------------------
# Cenário 2: repository NUNCA é tocado durante conversar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_repository_nunca_e_chamado():
    """Repository não deve receber nenhuma chamada durante conversar."""
    llm = _mock_llm("qualquer resposta")
    repo = _mock_repository()

    with patch("agent.tools.conversar.criar_llm", return_value=llm):
        from agent.tools.conversar import ToolConversar
        tool = ToolConversar(repository=repo)
        await tool.executar(mensagem="conceito de CET?", historico=[])

    repo.buscar.assert_not_called()
    repo.salvar.assert_not_called()
    repo.listar.assert_not_called()
    repo.excluir.assert_not_called()


# ---------------------------------------------------------------------------
# Cenário 3: histórico entra no contexto enviado ao LLM
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_historico_incluido_no_prompt():
    """O histórico fornecido deve aparecer no prompt enviado ao LLM."""
    llm = _mock_llm("Economize automatizando transferências")
    repo = _mock_repository()

    historico = [
        {"role": "user", "content": "primeira mensagem"},
        {"role": "assistant", "content": "primeira resposta"},
    ]

    captured_prompt = {}

    def fake_montar_prompt(acao, ctx):
        captured_prompt.update(ctx)
        return f"PROMPT_GERADO para {acao}"

    with patch("agent.tools.conversar.criar_llm", return_value=llm), \
         patch("agent.tools.conversar.montar_prompt", side_effect=fake_montar_prompt):
        from agent.tools.conversar import ToolConversar
        tool = ToolConversar(repository=repo)
        await tool.executar(mensagem="como economizar?", historico=historico)

    # O contexto passado ao montar_prompt deve conter o histórico de alguma forma
    assert "historico" in captured_prompt or "historico_recente" in captured_prompt, (
        "O histórico não foi passado ao montar_prompt via contexto"
    )


# ---------------------------------------------------------------------------
# Cenário 4: prompt construído via montar_prompt("conversar", ctx)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_montado_via_montar_prompt_conversar():
    """montar_prompt deve ser chamado com acao='conversar'."""
    llm = _mock_llm("dica financeira")
    repo = _mock_repository()

    with patch("agent.tools.conversar.criar_llm", return_value=llm), \
         patch("agent.tools.conversar.montar_prompt", return_value="prompt gerado") as mock_montar:
        from agent.tools.conversar import ToolConversar
        tool = ToolConversar(repository=repo)
        await tool.executar(mensagem="me dá uma dica", historico=[])

    mock_montar.assert_called_once()
    args, kwargs = mock_montar.call_args
    acao_chamada = args[0] if args else kwargs.get("acao")
    assert acao_chamada == "conversar", (
        f"montar_prompt deveria ter sido chamado com acao='conversar', mas foi '{acao_chamada}'"
    )


# ---------------------------------------------------------------------------
# Cenário 5: contexto de conversar NÃO contém "contexto_rag"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_prompt_conversar_nao_contem_contexto_rag():
    """O contexto passado ao montar_prompt não deve ter chave 'contexto_rag'."""
    llm = _mock_llm("resposta qualquer")
    repo = _mock_repository()

    captured_ctx = {}

    def fake_montar_prompt(acao, ctx):
        captured_ctx.update(ctx)
        return "prompt gerado"

    with patch("agent.tools.conversar.criar_llm", return_value=llm), \
         patch("agent.tools.conversar.montar_prompt", side_effect=fake_montar_prompt):
        from agent.tools.conversar import ToolConversar
        tool = ToolConversar(repository=repo)
        await tool.executar(mensagem="me dá uma dica", historico=[])

    assert "contexto_rag" not in captured_ctx, (
        "O contexto de conversar não deve conter 'contexto_rag'"
    )


# ---------------------------------------------------------------------------
# Cenário 6: modelo LLM vem de Settings.LLM_MODELO_CONVERSAR
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_usa_modelo_llm_modelo_conversar_de_settings():
    """criar_llm deve ser chamado com o modelo de Settings.LLM_MODELO_CONVERSAR."""
    repo = _mock_repository()
    llm = _mock_llm("resposta")

    captured_modelo = {}

    def fake_criar_llm(modelo, **kwargs):
        captured_modelo["modelo"] = modelo
        return llm

    with patch("agent.tools.conversar.criar_llm", side_effect=fake_criar_llm), \
         patch("agent.tools.conversar.montar_prompt", return_value="prompt"):
        from agent.tools.conversar import ToolConversar
        from agent.config import settings
        tool = ToolConversar(repository=repo)
        await tool.executar(mensagem="teste", historico=[])

    assert captured_modelo.get("modelo") == settings.LLM_MODELO_CONVERSAR, (
        f"criar_llm foi chamado com '{captured_modelo.get('modelo')}' "
        f"em vez de Settings.LLM_MODELO_CONVERSAR='{settings.LLM_MODELO_CONVERSAR}'"
    )


# ---------------------------------------------------------------------------
# Cenário 7: resposta em linguagem natural (campo "resposta" é string não vazia)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resposta_e_string_nao_vazia():
    """dados['resposta'] deve ser uma string não vazia."""
    llm = _mock_llm("Parcelar pode ser vantajoso se o CET for zero.")
    repo = _mock_repository()

    with patch("agent.tools.conversar.criar_llm", return_value=llm):
        from agent.tools.conversar import ToolConversar
        tool = ToolConversar(repository=repo)
        resultado = await tool.executar(
            mensagem="vale a pena parcelar?",
            historico=[],
        )

    assert isinstance(resultado.dados["resposta"], str)
    assert len(resultado.dados["resposta"]) > 0
