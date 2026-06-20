import os

# Set env vars before any import that loads Settings
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake-key-for-tests")
os.environ.setdefault("EVOLUTION_API_URL", "http://fake-evolution")
os.environ.setdefault("EVOLUTION_INSTANCE", "fake-instance")
os.environ.setdefault("EVOLUTION_API_KEY", "fake-api-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511999999999")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Jhonatas")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "test@exemplo.com")
os.environ.setdefault("WEBHOOK_APIKEY", "test-apikey")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from agent.domain.intencao import ItemCadastro, ParamsCadastrar
from agent.services.extrator import Extrator


def _llm_mock(itens: list[dict]):
    chain = AsyncMock()
    chain.ainvoke = AsyncMock(
        return_value=ParamsCadastrar(itens=[ItemCadastro(**i) for i in itens])
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = chain
    return llm, chain


@pytest.mark.asyncio
async def test_extrator_preenche_campo_none():
    """LLM retorna forma_pagamento=PIX; item parcial não tinha → resultado tem PIX."""
    llm, _ = _llm_mock(
        [{"descricao": "mercado", "valor": Decimal("200"), "forma_pagamento": "PIX"}]
    )
    resultado = await Extrator(llm).extrair_cadastro(
        [ItemCadastro(descricao="mercado", valor=Decimal("200"))], "comprei", []
    )
    assert resultado[0].forma_pagamento == "PIX"


@pytest.mark.asyncio
async def test_extrator_nao_sobrescreve_valor_existente():
    """LLM retorna valor=None; item parcial tinha valor=150 → resultado mantém 150."""
    llm, _ = _llm_mock(
        [{"descricao": "roupa", "valor": None, "forma_pagamento": "CARTAO_CREDITO"}]
    )
    resultado = await Extrator(llm).extrair_cadastro(
        [ItemCadastro(descricao="roupa", valor=Decimal("150"))], "comprei roupa", []
    )
    assert resultado[0].valor == Decimal("150")


@pytest.mark.asyncio
async def test_extrator_inclui_historico_no_prompt():
    """O prompt enviado ao LLM deve conter o texto do histórico."""
    llm, chain = _llm_mock([{"descricao": "roupa"}])
    await Extrator(llm).extrair_cadastro(
        [ItemCadastro(descricao="roupa")],
        "foi 350",
        ["usuario: comprei roupa", "assistente: quanto custou?"],
    )
    prompt = chain.ainvoke.call_args[0][0]
    assert "comprei roupa" in prompt
