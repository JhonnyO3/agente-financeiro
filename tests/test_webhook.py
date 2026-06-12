import os
import pytest
from unittest.mock import AsyncMock

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

from httpx import AsyncClient, ASGITransport
from agent.entrypoint.main import app

AUTHORIZED_NUMBER = "5511957818539"

PAYLOAD_AUTHORIZED = {
    "event": "messages.upsert",
    "data": {
        "key": {
            "remoteJid": f"{AUTHORIZED_NUMBER}@s.whatsapp.net",
            "fromMe": False,
            "id": "MSG_001",
        },
        "message": {"conversation": "oi"},
        "messageTimestamp": 1718000000,
    },
}

PAYLOAD_UNAUTHORIZED = {
    "event": "messages.upsert",
    "data": {
        "key": {
            "remoteJid": "5511999999999@s.whatsapp.net",
            "fromMe": False,
            "id": "MSG_002",
        },
        "message": {"conversation": "oi"},
        "messageTimestamp": 1718000001,
    },
}

PAYLOAD_AUDIO = {
    "event": "messages.upsert",
    "data": {
        "key": {
            "remoteJid": f"{AUTHORIZED_NUMBER}@s.whatsapp.net",
            "fromMe": False,
            "id": "MSG_003",
        },
        "message": {"audioMessage": {"seconds": 5}},
        "messageTimestamp": 1718000002,
    },
}


def _setup_app_state():
    mock_debouncer = AsyncMock()
    mock_debouncer.receber = AsyncMock()
    app.state.debouncer = mock_debouncer
    app.state.processar_e_responder = AsyncMock()
    return mock_debouncer


@pytest.mark.asyncio
async def test_numero_nao_autorizado_retorna_200_sem_chamar_pipeline():
    mock_debouncer = _setup_app_state()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/webhook/mensagem", json=PAYLOAD_UNAUTHORIZED)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_debouncer.receber.assert_not_called()


@pytest.mark.asyncio
async def test_mensagem_audio_retorna_200_sem_chamar_pipeline():
    mock_debouncer = _setup_app_state()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/webhook/mensagem", json=PAYLOAD_AUDIO)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_debouncer.receber.assert_not_called()
