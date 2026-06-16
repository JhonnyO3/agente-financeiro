"""
Testes TDD — Task CC-03: Webhook resolve identidade in-process.

Cenários baseados em specs/cadastro-e-multiusuario/scenarios/03-webhook-resolve-identidade.feature

- Número não cadastrado → 200 sem enfileirar
- Usuário inativo → 200 sem enfileirar (repo retorna None)
- Usuário ativo → enfileira (usuario_id, numero, texto)
- apikey inválida → 401
- fromMe, evento errado, texto vazio, duplicado → 200 sem enfileirar
- Nenhuma referência a WHATSAPP_ALLOWED_NUMBER no webhook
"""

import os
from unittest.mock import AsyncMock, MagicMock

# Todas as env vars obrigatórias ANTES de qualquer import do projeto
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake-key-for-tests")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Jhonatas")
os.environ.setdefault("WEBHOOK_APIKEY", "test-apikey")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "test@exemplo.com")
os.environ.setdefault("DEBOUNCE_SEGUNDOS", "1")

from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from agent.entrypoint.webhook import router as webhook_router

VALID_APIKEY = "test-apikey"
NUMERO = "5511999998888"
USUARIO_ID = 42


def _make_app(usuario_fake=None):
    """Cria app mínimo de teste com state mockado."""
    app = FastAPI()
    app.include_router(webhook_router, prefix="/webhook")

    mock_fila = AsyncMock()
    mock_fila.put = AsyncMock()
    app.state.fila = mock_fila

    # session_factory mock: retorna context manager que devolve sessão
    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory = MagicMock(return_value=mock_ctx)
    app.state.session_factory = mock_session_factory

    # resolver_usuario_por_telefone é patchado nos testes via monkeypatch
    app.state._usuario_fake = usuario_fake

    return app, mock_fila


def _make_payload(
    event: str = "messages.upsert",
    from_me: bool = False,
    number: str = NUMERO,
    message_id: str = "MSG_TEST_001",
    text: str = "gastei 50",
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


def _make_usuario(id: int = USUARIO_ID):
    u = MagicMock()
    u.id = id
    return u


# ---------------------------------------------------------------------------
# Cenário: apikey inválida → 401
# ---------------------------------------------------------------------------


async def test_apikey_invalida_retorna_401(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_make_usuario()),
    )
    payload = _make_payload()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": "chave-errada"},
        )

    assert response.status_code == 401
    mock_fila.put.assert_not_awaited()


async def test_apikey_ausente_retorna_401(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_make_usuario()),
    )
    payload = _make_payload()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/webhook/mensagem", json=payload)

    assert response.status_code == 401
    mock_fila.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Cenário: número não cadastrado → 200 sem enfileirar
# ---------------------------------------------------------------------------


async def test_numero_nao_cadastrado_retorna_200_sem_enfileirar(monkeypatch):
    app, mock_fila = _make_app(usuario_fake=None)
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=None),
    )
    payload = _make_payload(number="5511000000000", message_id="MSG_NAO_CADASTRADO")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_fila.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Cenário: usuário inativo → repo retorna None → 200 sem enfileirar
# ---------------------------------------------------------------------------


async def test_usuario_inativo_retorna_200_sem_enfileirar(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=None),
    )
    payload = _make_payload(number=NUMERO, message_id="MSG_INATIVO")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_fila.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Cenário: usuário ativo → enfileira (usuario_id, numero, texto)
# ---------------------------------------------------------------------------


async def test_usuario_ativo_enfileira_tupla_com_usuario_id(monkeypatch):
    app, mock_fila = _make_app()
    usuario = _make_usuario(id=USUARIO_ID)
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=usuario),
    )
    payload = _make_payload(number=NUMERO, text="gastei 50", message_id="MSG_ATIVO")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_fila.put.assert_awaited_once_with((USUARIO_ID, NUMERO, "gastei 50"))


# ---------------------------------------------------------------------------
# Cenário: fromMe → 200 sem enfileirar
# ---------------------------------------------------------------------------


async def test_from_me_retorna_200_sem_enfileirar(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_make_usuario()),
    )
    payload = _make_payload(from_me=True, message_id="MSG_FROMME")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_fila.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Cenário: evento diferente → 200 sem enfileirar
# ---------------------------------------------------------------------------


async def test_evento_diferente_retorna_200_sem_enfileirar(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_make_usuario()),
    )
    payload = _make_payload(event="messages.update", message_id="MSG_EVENTO")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_fila.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Cenário: texto vazio → 200 sem enfileirar
# ---------------------------------------------------------------------------


async def test_texto_vazio_retorna_200_sem_enfileirar(monkeypatch):
    app, mock_fila = _make_app()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_make_usuario()),
    )
    payload = _make_payload(text="", message_id="MSG_SEMTEXTO")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_fila.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Cenário: dedup por message_id
# ---------------------------------------------------------------------------


async def test_mensagem_duplicada_enfileirada_uma_vez(monkeypatch):
    app, mock_fila = _make_app()
    usuario = _make_usuario()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=usuario),
    )
    payload = _make_payload(message_id="MSG_DEDUP_CC03")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
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
    assert mock_fila.put.await_count == 1


# ---------------------------------------------------------------------------
# Cenário: sem referência a WHATSAPP_ALLOWED_NUMBER no webhook
# ---------------------------------------------------------------------------


def test_webhook_nao_referencia_whatsapp_allowed_number():
    import inspect
    import agent.entrypoint.webhook as wh_module

    source = inspect.getsource(wh_module)
    assert "WHATSAPP_ALLOWED_NUMBER" not in source, (
        "webhook.py ainda referencia WHATSAPP_ALLOWED_NUMBER — deve ser removido"
    )


# ---------------------------------------------------------------------------
# Cenário: proteção de PII — payload não logado em INFO
# ---------------------------------------------------------------------------


async def test_payload_nao_logado_em_info(monkeypatch, caplog):
    app, mock_fila = _make_app()
    usuario = _make_usuario()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=usuario),
    )
    payload = _make_payload(text="meu salario secreto", message_id="MSG_PII_CC03")

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

    payload_str = str(payload)
    for record in caplog.records:
        if record.levelno == logging.INFO:
            assert payload_str not in record.getMessage(), (
                "Payload completo foi logado em INFO — viola proteção de PII"
            )
