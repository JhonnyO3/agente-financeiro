"""Fixtures compartilhadas para a suite de testes."""

from __future__ import annotations

import os

import pytest

# Variáveis de ambiente necessárias para importar o app sem banco real
_ENV_DEFAULTS = {
    "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
    "EVOLUTION_API_URL": "http://localhost:8080",
    "EVOLUTION_INSTANCE": "test",
    "EVOLUTION_API_KEY": "test-key",
    "OPENAI_API_KEY": "sk-fake-key-for-tests",
    "RESPONSAVEL_PADRAO": "",
    "WEBHOOK_APIKEY": "test-apikey",
    "REDIS_URL": "redis://localhost:6379/0",
    "AGENTE_USUARIO_EMAIL": "test@exemplo.com",
    "DEBOUNCE_SEGUNDOS": "1",
}

for _k, _v in _ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)


@pytest.fixture(autouse=True)
def _limpar_dedup_webhook():
    """Garante que o dedup do webhook seja limpo entre testes."""
    from agent.entrypoint import webhook as _wh
    _wh._seen.clear()
    yield
    _wh._seen.clear()
