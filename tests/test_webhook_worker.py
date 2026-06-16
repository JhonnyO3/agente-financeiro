"""
Testes vermelhos (TDD) — Task 14: Webhook auth/dedup/fila + Worker debounce/pipeline.

Descreve o NOVO comportamento esperado:
- webhook.py: auth por header apikey, dedup por message_id, filtros silenciosos,
  sem log de payload em INFO.
- worker.py: debounce agrupa fragmentos por "\n", chama pipeline completo,
  registra histórico, envia erro amigável em exceção.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

# Todas as env vars obrigatórias ANTES de qualquer import do projeto
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511957818539")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake-key-for-tests")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Jhonatas")
os.environ.setdefault("WEBHOOK_APIKEY", "test-apikey")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "test@exemplo.com")
os.environ.setdefault("DEBOUNCE_SEGUNDOS", "1")

from httpx import AsyncClient, ASGITransport
from agent.entrypoint.main import app

AUTHORIZED_NUMBER = "5511957818539"
VALID_APIKEY = "test-apikey"


def _make_payload(
    event: str = "messages.upsert",
    from_me: bool = False,
    number: str = AUTHORIZED_NUMBER,
    message_id: str = "MSG_TEST_001",
    text: str = "listar gastos",
) -> dict:
    payload: dict = {
        "event": event,
        "data": {
            "key": {
                "remoteJid": f"{number}@s.whatsapp.net",
                "fromMe": from_me,
                "id": message_id,
            },
            "messageTimestamp": 1718000000,
        },
    }
    if text:
        payload["data"]["message"] = {"conversation": text}
    return payload


def _setup_app_state():
    """Mocks mínimos: a fila (queue) e o worker não existem ainda → vai falhar."""
    mock_queue = AsyncMock()
    mock_queue.put = AsyncMock()
    app.state.fila = mock_queue

    mock_worker = AsyncMock()
    app.state.worker = mock_worker

    # Mantém estado_store e evolution_client como mocks para os testes de worker
    mock_estado_store = AsyncMock()
    mock_estado_store.registrar_mensagem = AsyncMock()
    app.state.estado_store = mock_estado_store

    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()
    app.state.evolution_client = mock_evolution

    return mock_queue, mock_estado_store, mock_evolution


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


async def test_apikey_correta_retorna_200_e_enfileira():
    mock_queue, _, _ = _setup_app_state()
    payload = _make_payload()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_queue.put.assert_awaited_once()


async def test_apikey_ausente_retorna_401():
    mock_queue, _, _ = _setup_app_state()
    payload = _make_payload()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhook/mensagem", json=payload)

    assert response.status_code == 401
    mock_queue.put.assert_not_awaited()


async def test_apikey_errada_retorna_401():
    mock_queue, _, _ = _setup_app_state()
    payload = _make_payload()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": "chave-invalida"},
        )

    assert response.status_code == 401
    mock_queue.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Filtros silenciosos (200 sem enfileirar)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "override,description",
    [
        ({"event": "messages.update"}, "evento diferente de messages.upsert"),
        ({"from_me": True}, "fromMe=True"),
        ({"number": "5511000000000"}, "numero nao autorizado"),
        ({"text": ""}, "sem texto"),
    ],
)
async def test_filtros_silenciosos_retornam_200_sem_enfileirar(override, description):
    mock_queue, _, _ = _setup_app_state()
    payload = _make_payload(**override)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200, f"falhou para caso: {description}"
    mock_queue.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Dedup por message_id
# ---------------------------------------------------------------------------


async def test_message_id_duplicado_enfileirado_apenas_uma_vez():
    mock_queue, _, _ = _setup_app_state()
    payload = _make_payload(message_id="MSG_DEDUP_001")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )
        r2 = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    # Apenas UMA vez na fila
    assert mock_queue.put.await_count == 1


async def test_message_ids_distintos_sao_ambos_enfileirados():
    mock_queue, _, _ = _setup_app_state()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post(
            "/webhook/mensagem",
            json=_make_payload(message_id="MSG_A"),
            headers={"apikey": VALID_APIKEY},
        )
        r2 = await client.post(
            "/webhook/mensagem",
            json=_make_payload(message_id="MSG_B"),
            headers={"apikey": VALID_APIKEY},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert mock_queue.put.await_count == 2


# ---------------------------------------------------------------------------
# Proteção de PII: payload NÃO logado em INFO
# ---------------------------------------------------------------------------


async def test_payload_completo_nao_logado_em_info(caplog):
    _setup_app_state()
    payload = _make_payload(text="meu salario secreto", message_id="MSG_PII_001")

    import logging

    with caplog.at_level(logging.INFO, logger="agent.entrypoint.webhook"):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                "/webhook/mensagem",
                json=payload,
                headers={"apikey": VALID_APIKEY},
            )

    # Nenhum registro INFO deve conter o texto completo do payload
    payload_str = str(payload)
    for record in caplog.records:
        if record.levelno == logging.INFO:
            assert payload_str not in record.getMessage(), (
                "Payload completo foi logado em INFO — viola proteção de PII"
            )
    # Número e texto do usuário não devem aparecer em log de payload bruto
    texto_usuario = "meu salario secreto"
    numero_usuario = AUTHORIZED_NUMBER
    for record in caplog.records:
        if record.levelno == logging.INFO and "webhook recebido" in record.getMessage():
            assert texto_usuario not in record.getMessage(), (
                "Texto do usuário aparece em log de payload bruto (nível INFO)"
            )
            assert numero_usuario not in record.getMessage(), (
                "Número do usuário aparece em log de payload bruto (nível INFO)"
            )

