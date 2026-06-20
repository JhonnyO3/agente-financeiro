"""
Testes de integração do webhook.

Cenário 1: usuário conhecido, payload válido → mensagem enfileirada.
Cenário 2: usuário desconhecido → 200 sem enfileirar; mensagem duplicada enfileirada uma vez.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

NUMERO = "5511999998888"
USUARIO_ID = 42


def _make_app():
    from agent.entrypoint.webhook import router as webhook_router

    app = FastAPI()
    app.include_router(webhook_router, prefix="/webhook")

    mock_fila = AsyncMock()
    mock_fila.put = AsyncMock()
    app.state.fila = mock_fila

    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    app.state.session_factory = MagicMock(return_value=mock_ctx)

    return app, mock_fila


def _payload(
    event: str = "messages.upsert",
    number: str = NUMERO,
    text: str = "gastei 50",
    message_id: str = "MSG001",
    from_me: bool = False,
) -> dict:
    p: dict = {
        "event": event,
        "data": {
            "key": {"remoteJid": f"{number}@s.whatsapp.net", "fromMe": from_me, "id": message_id},
            "messageTimestamp": 1718000000,
        },
    }
    if text:
        p["data"]["message"] = {"conversation": text}
    return p


def _usuario(id: int = USUARIO_ID):
    u = MagicMock()
    u.id = id
    return u


# ---------------------------------------------------------------------------
# Cenário 1: fluxo feliz — usuário conhecido, mensagem enfileirada
# ---------------------------------------------------------------------------


async def test_usuario_conhecido_mensagem_enfileirada(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_usuario()),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/webhook/mensagem", json=_payload(number=NUMERO, text="gastei 50"))

    assert r.status_code == 200
    mock_fila.put.assert_awaited_once_with((USUARIO_ID, NUMERO, "gastei 50"))


# ---------------------------------------------------------------------------
# Cenário 2: rejeição — usuário desconhecido; dedup garante única enfileirada
# ---------------------------------------------------------------------------


async def test_usuario_desconhecido_retorna_200_sem_enfileirar(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=None),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/webhook/mensagem", json=_payload(number="5511000000000"))

    assert r.status_code == 200
    mock_fila.put.assert_not_awaited()


async def test_mensagem_duplicada_enfileirada_uma_vez(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_usuario()),
    )
    p = _payload(message_id="MSG_DEDUP")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/webhook/mensagem", json=p)
        await c.post("/webhook/mensagem", json=p)

    assert mock_fila.put.await_count == 1
