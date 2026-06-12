"""
Testes VERMELHOS (TDD) — Task 15: EvolutionApiClient robusto.

Fase red: a implementação atual engole exceções e não tem retry.
Estes testes DEVEM FALHAR até que a implementação seja corrigida.
"""
import asyncio
import os

os.environ.setdefault("EVOLUTION_API_URL", "http://fake-evolution")
os.environ.setdefault("EVOLUTION_INSTANCE", "fake-instance")
os.environ.setdefault("EVOLUTION_API_KEY", "fake-key")
os.environ.setdefault("WEBHOOK_APIKEY", "fake-webhook-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511999999999")
os.environ.setdefault("OPENAI_API_KEY", "fake-openai-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://fake/fake")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "admin@exemplo.com")
os.environ.setdefault("ADMIN_EMAILS", "admin@exemplo.com")

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from agent.integrations.evolution_client import EvolutionApiClient


def _make_response(status_code: int) -> httpx.Response:
    """Cria um httpx.Response com status_code dado."""
    return httpx.Response(status_code, request=httpx.Request("POST", "http://fake"))


def _make_client(side_effect) -> EvolutionApiClient:
    """Retorna um EvolutionApiClient com self._client.post mockado."""
    client = EvolutionApiClient(
        base_url="http://fake-evolution",
        instance="fake-instance",
        api_key="fake-key",
    )
    client._client = AsyncMock()
    client._client.post = AsyncMock(side_effect=side_effect)
    return client


# ---------------------------------------------------------------------------
# Cenário 1: HTTP 200 → nenhuma exceção
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_envio_200_nao_levanta_excecao():
    """HTTP 200 deve completar sem exceção."""
    client = _make_client(side_effect=[_make_response(200)])

    # Não deve levantar nenhuma exceção
    await client.enviar_mensagem("5511999999999", "ola")

    client._client.post.assert_called_once()


# ---------------------------------------------------------------------------
# Cenário 2: HTTP 4xx → exceção imediata, sem retry
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_envio_4xx_levanta_excecao_sem_retry():
    """HTTP 400 deve levantar exceção e NÃO fazer retry (post chamado 1x)."""
    client = _make_client(side_effect=[_make_response(400)])

    with pytest.raises(Exception):
        await client.enviar_mensagem("5511999999999", "ola")

    # Sem retry: post chamado exatamente uma vez
    assert client._client.post.call_count == 1


# ---------------------------------------------------------------------------
# Cenário 3: HTTP 500 sempre → retry com backoff, exceção após esgotar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_envio_5xx_retry_backoff_e_propaga_excecao():
    """HTTP 500 permanente: asyncio.sleep chamado >=1x; exceção propagada ao esgotar."""
    client = _make_client(side_effect=lambda *a, **kw: _make_response(500))

    sleep_calls = []

    async def fake_sleep(delay):
        sleep_calls.append(delay)

    with patch("asyncio.sleep", new=fake_sleep):
        with pytest.raises(Exception):
            await client.enviar_mensagem("5511999999999", "ola")

    # Deve ter dormido pelo menos 1 vez (backoff entre tentativas)
    assert len(sleep_calls) >= 1, "asyncio.sleep deve ser chamado para backoff entre retries"

    # Deve ter tentado mais de uma vez
    assert client._client.post.call_count > 1, (
        f"Esperava múltiplas tentativas, mas post foi chamado {client._client.post.call_count}x"
    )


# ---------------------------------------------------------------------------
# Cenário 4: HTTP 503 na 1ª, 200 na 2ª → sucesso com 2 chamadas
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_envio_503_depois_200_sucesso_na_segunda_tentativa():
    """503 na 1ª tentativa, 200 na 2ª → não levanta exceção e post chamado 2x."""
    respostas = [_make_response(503), _make_response(200)]
    client = _make_client(side_effect=respostas)

    async def fake_sleep(delay):
        pass  # não dormir de verdade

    with patch("asyncio.sleep", new=fake_sleep):
        # Não deve levantar exceção (recuperou na 2ª tentativa)
        await client.enviar_mensagem("5511999999999", "ola")

    assert client._client.post.call_count == 2, (
        f"Esperava 2 chamadas (1 falha + 1 sucesso), got {client._client.post.call_count}"
    )


# ---------------------------------------------------------------------------
# Cenário 5: timeout explícito configurado no client
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_timeout_explícito_propagado():
    """ReadTimeout do httpx deve ser propagado como exceção (não silenciado)."""
    request = httpx.Request("POST", "http://fake-evolution/message/sendText/fake-instance")

    async def post_raises_timeout(*args, **kwargs):
        raise httpx.ReadTimeout("timed out", request=request)

    client = _make_client(side_effect=post_raises_timeout)

    async def fake_sleep(delay):
        pass

    # Deve propagar httpx.ReadTimeout (ou qualquer exceção de timeout)
    with patch("asyncio.sleep", new=fake_sleep):
        with pytest.raises((httpx.ReadTimeout, httpx.TimeoutException, Exception)):
            await client.enviar_mensagem("5511999999999", "ola")


@pytest.mark.asyncio
async def test_client_tem_timeout_configurado():
    """O AsyncClient interno deve ter timeout explícito (não None/infinito)."""
    client = EvolutionApiClient(
        base_url="http://fake-evolution",
        instance="fake-instance",
        api_key="fake-key",
    )
    # O timeout do cliente interno deve ser um valor finito e positivo
    timeout = client._client.timeout
    # httpx.Timeout ou float — qualquer representação deve ser finita e > 0
    if isinstance(timeout, httpx.Timeout):
        assert timeout.read is not None and timeout.read > 0
    else:
        assert timeout is not None and float(timeout) > 0
    await client.fechar()
