"""
Fixtures para testes de agente.

Usa OpenAI e Redis reais — Evolution API é mockada.
Requer OPENAI_API_KEY e REDIS_URL no ambiente.

Execute apenas quando as variáveis estiverem disponíveis:
    uv run pytest tests/agent/ -v
"""

from __future__ import annotations

import os

import pytest

# Pula a suite inteira se não houver chave real da OpenAI
_OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
pytestmark = pytest.mark.skipif(
    not _OPENAI_KEY or _OPENAI_KEY.startswith("sk-fake"),
    reason="OPENAI_API_KEY real necessária para testes de agente",
)
