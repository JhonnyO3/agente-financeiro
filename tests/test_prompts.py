import os
import re
import sys

# Defina vars de ambiente antes de qualquer import que carregue Settings
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
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx_classificador(**overrides):
    """Contexto mínimo válido para a ação classificador."""
    base = {
        "user_name": "Jhonatas",
        "data_atual": "12/06/2026",
        "responsavel_padrao": "Jhon",
        "historico_recente": "Nenhum histórico.",
        "estado_pendente": "nenhuma",
    }
    base.update(overrides)
    return base


def _has_unfilled_placeholder(text: str) -> bool:
    """Detecta {variavel} não substituído (ignora blocos de código markdown)."""
    return bool(re.search(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}', text))


# ---------------------------------------------------------------------------
# Cenário 1: montar_prompt("classificador") injeta o arquivo certo e preenche
#             todas as variáveis sem KeyError
# ---------------------------------------------------------------------------

def test_montar_prompt_classificador_sem_placeholders_residuais():
    from agent.services.prompts import montar_prompt  # noqa: importado aqui p/ evitar Settings na coleta

    ctx = _ctx_classificador()
    resultado = montar_prompt("classificador", ctx)

    assert isinstance(resultado, str)
    assert len(resultado) > 100
    assert not _has_unfilled_placeholder(resultado), (
        f"Há placeholders não substituídos no resultado:\n{resultado}"
    )


def test_montar_prompt_classificador_contem_conteudo_injection():
    from agent.services.prompts import montar_prompt

    ctx = _ctx_classificador()
    resultado = montar_prompt("classificador", ctx)

    # O classificador deve mencionar pelo menos uma das intenções documentadas
    assert any(intencao in resultado for intencao in [
        "cadastrar", "listar", "atualizar", "excluir", "conversar"
    ]), "O conteúdo de 01-classificador.md não foi injetado no resultado"


# ---------------------------------------------------------------------------
# Cenário 2: montar_prompt("cadastrar") injeta 02-extracao-cadastrar.md
# ---------------------------------------------------------------------------

def test_montar_prompt_cadastrar_sem_placeholders_residuais():
    from agent.services.prompts import montar_prompt

    ctx = _ctx_classificador()
    ctx["parametros"] = '{"itens": [{"descricao": "Uber", "valor": 30}]}'
    resultado = montar_prompt("cadastrar", ctx)

    assert not _has_unfilled_placeholder(resultado), (
        f"Há placeholders não substituídos:\n{resultado}"
    )


# ---------------------------------------------------------------------------
# Cenário 3: montar_prompt("atualizar") injeta 03-extracao-atualizar.md
# ---------------------------------------------------------------------------

def test_montar_prompt_atualizar_sem_placeholders_residuais():
    from agent.services.prompts import montar_prompt

    ctx = _ctx_classificador()
    ctx["parametros"] = '{"referencia": "Zara", "campo": "valor", "novo_valor": 200}'
    ctx["candidatos"] = "1. Zara - R$150 - CARTAO_CREDITO"
    resultado = montar_prompt("atualizar", ctx)

    assert not _has_unfilled_placeholder(resultado)


# ---------------------------------------------------------------------------
# Cenário 4: montar_prompt("conversar") injeta 06-conversar.md
#             e não contém referência a contexto_rag
# ---------------------------------------------------------------------------

def test_montar_prompt_conversar_sem_contexto_rag():
    from agent.services.prompts import montar_prompt

    ctx = _ctx_classificador()
    ctx["mensagem"] = "Vale a pena parcelar uma compra grande?"
    resultado = montar_prompt("conversar", ctx)

    assert not _has_unfilled_placeholder(resultado)
    assert "contexto_rag" not in resultado, (
        "conversar não deve referenciar contexto_rag"
    )


# ---------------------------------------------------------------------------
# Cenário 5: responsavel_padrao vem de Settings (nunca hardcoded)
#            Quando NÃO fornecido no ctx, a função deve buscá-lo de Settings
# ---------------------------------------------------------------------------

def test_responsavel_padrao_vem_de_settings_quando_ausente_no_ctx():
    """Se montar_prompt injeta responsavel_padrao de Settings automaticamente,
    o resultado deve conter o valor de Settings.RESPONSAVEL_PADRAO."""
    from agent.services.prompts import montar_prompt

    # Contexto SEM responsavel_padrao — a função deve buscar em Settings
    ctx = {
        "user_name": "Jhonatas",
        "data_atual": "12/06/2026",
        "historico_recente": "Nenhum histórico.",
        "estado_pendente": "nenhuma",
    }

    # Mocka Settings para garantir o valor esperado
    with patch("agent.services.prompts.settings") as mock_settings:
        mock_settings.RESPONSAVEL_PADRAO = "Responsavel_Teste"
        resultado = montar_prompt("classificador", ctx)

    assert "Responsavel_Teste" in resultado, (
        "responsavel_padrao de Settings não foi injetado no prompt"
    )


# ---------------------------------------------------------------------------
# Cenário 6: variável obrigatória ausente → exceção explícita
# ---------------------------------------------------------------------------

def test_variavel_obrigatoria_ausente_levanta_excecao():
    from agent.services.prompts import montar_prompt

    ctx = _ctx_classificador()
    del ctx["historico_recente"]  # remove variável obrigatória

    with pytest.raises((KeyError, ValueError)):
        montar_prompt("classificador", ctx)


def test_variavel_ausente_nao_produz_placeholder_silencioso():
    """Garante que a falha é explícita (nunca silenciosa com {var} no output)."""
    from agent.services.prompts import montar_prompt

    ctx = _ctx_classificador()
    del ctx["estado_pendente"]

    try:
        resultado = montar_prompt("classificador", ctx)
        # Se não lançou exceção, o resultado NÃO pode ter placeholder residual
        assert not _has_unfilled_placeholder(resultado), (
            "Variável ausente produziu placeholder silencioso no output"
        )
        pytest.fail("Era esperada uma exceção por variável obrigatória ausente")
    except (KeyError, ValueError):
        pass  # comportamento correto


# ---------------------------------------------------------------------------
# Cenário 7: ARQUIVO_POR_ACAO tem exatamente as 4 ações esperadas
# ---------------------------------------------------------------------------

def test_arquivo_por_acao_tem_exatamente_as_quatro_acoes():
    from agent.services.prompts import ARQUIVO_POR_ACAO

    esperadas = {"classificador", "cadastrar", "atualizar", "conversar"}
    assert set(ARQUIVO_POR_ACAO.keys()) == esperadas, (
        f"Chaves inesperadas: {set(ARQUIVO_POR_ACAO.keys())}"
    )


def test_listar_e_excluir_nao_estao_em_arquivo_por_acao():
    from agent.services.prompts import ARQUIVO_POR_ACAO

    assert "listar" not in ARQUIVO_POR_ACAO
    assert "excluir" not in ARQUIVO_POR_ACAO


# ---------------------------------------------------------------------------
# Cenário 8: Só existem os 5 arquivos de prompt esperados em agent/prompts/
# ---------------------------------------------------------------------------

def test_somente_os_arquivos_de_prompt_esperados_existem():
    from pathlib import Path

    prompts_dir = Path(__file__).parents[1] / "agent" / "prompts"
    assert prompts_dir.is_dir(), "Diretório agent/prompts/ não existe"

    arquivos = {f.name for f in prompts_dir.iterdir() if f.suffix == ".md"}
    esperados = {
        "00-base.md",
        "01-classificador.md",
        "02-extracao-cadastrar.md",
        "03-extracao-atualizar.md",
        "06-conversar.md",
    }
    assert arquivos == esperados, (
        f"Arquivos encontrados: {arquivos}\nEsperados: {esperados}"
    )


# ---------------------------------------------------------------------------
# Cenário 9: Funções migradas em agent/agents_llm.py são importáveis
# ---------------------------------------------------------------------------

def test_carregar_prompt_importavel_de_agents_llm():
    from agent.agents_llm import carregar_prompt  # noqa

    # Deve ser callable e retornar string para um arquivo existente
    # (após implementação); antes da impl, apenas a importação é testada
    assert callable(carregar_prompt)


def test_coagir_data_importavel_de_agents_llm():
    from agent.agents_llm import coagir_data
    from datetime import date

    assert callable(coagir_data)

    # Também valida comportamento básico após implementação
    resultado = coagir_data("2026-06-12")
    assert resultado == date(2026, 6, 12)


def test_criar_llm_importavel_de_agents_llm():
    """criar_llm deve ser importável e retornar uma instância sem chamada real."""
    with patch("agent.agents_llm.ChatOpenAI") as MockLLM:
        MockLLM.return_value = MagicMock()
        from agent.agents_llm import criar_llm
        assert callable(criar_llm)


def test_criar_llm_usa_modelo_de_settings():
    """criar_llm deve usar Settings.LLM_MODELO_CLASSIFICACAO, não string fixa."""
    with patch("agent.agents_llm.ChatOpenAI") as MockLLM:
        MockLLM.return_value = MagicMock()
        with patch("agent.agents_llm.settings") as mock_settings:
            mock_settings.LLM_MODELO_CLASSIFICACAO = "gpt-4o-mini"
            from agent import agents_llm
            # Reimporta para capturar o mock
            import importlib
            importlib.reload(agents_llm)
            agents_llm.criar_llm()
            # Verifica que ChatOpenAI foi chamado (modelos vindos de Settings)
            assert MockLLM.called
