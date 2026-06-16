"""
Testes — Webhook auth/dedup/fila + Worker debounce/pipeline.

Webhook: auth por header apikey, dedup por message_id, filtros silenciosos,
resolução de identidade in-process (sem WHATSAPP_ALLOWED_NUMBER), sem log
de payload em INFO.

Worker: debounce agrupa fragmentos por "\n", chama pipeline completo,
registra histórico, envia erro amigável em exceção.
"""

import os
import pytest
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
from agent.entrypoint.main import app

NUMERO = "5511957818539"
USUARIO_ID = 1
VALID_APIKEY = "test-apikey"


def _make_usuario(id: int = USUARIO_ID):
    u = MagicMock()
    u.id = id
    return u


def _make_payload(
    event: str = "messages.upsert",
    from_me: bool = False,
    number: str = NUMERO,
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


def _setup_app_state(usuario_fake=None):
    """
    Mocks mínimos em app.state para os testes de integração que usam o app real.
    Injeta session_factory mockado + fila + resolver de identidade.
    """
    mock_queue = AsyncMock()
    mock_queue.put = AsyncMock()
    app.state.fila = mock_queue

    mock_worker = AsyncMock()
    app.state.worker = mock_worker

    mock_estado_store = AsyncMock()
    mock_estado_store.registrar_mensagem = AsyncMock()
    app.state.estado_store = mock_estado_store

    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()
    app.state.evolution_client = mock_evolution

    # session_factory mock para resolver_usuario_por_telefone
    mock_session = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_session_factory = MagicMock(return_value=mock_ctx)
    app.state.session_factory = mock_session_factory

    return mock_queue, mock_estado_store, mock_evolution


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------


async def test_apikey_correta_usuario_ativo_retorna_200_e_enfileira(monkeypatch):
    mock_queue, _, _ = _setup_app_state()
    usuario = _make_usuario(USUARIO_ID)
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=usuario),
    )
    payload = _make_payload(message_id="MSG_AUTH_OK")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_queue.put.assert_awaited_once()
    # Garante que a tupla tem 3 elementos: (usuario_id, numero, texto)
    args = mock_queue.put.call_args[0][0]
    assert len(args) == 3
    assert args[0] == USUARIO_ID


async def test_apikey_ausente_retorna_401(monkeypatch):
    mock_queue, _, _ = _setup_app_state()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_make_usuario()),
    )
    payload = _make_payload(message_id="MSG_AUTH_AUSENTE")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/webhook/mensagem", json=payload)

    assert response.status_code == 401
    mock_queue.put.assert_not_awaited()


async def test_apikey_errada_retorna_401(monkeypatch):
    mock_queue, _, _ = _setup_app_state()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_make_usuario()),
    )
    payload = _make_payload(message_id="MSG_AUTH_ERRADA")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
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
        ({"text": ""}, "sem texto"),
    ],
)
async def test_filtros_silenciosos_retornam_200_sem_enfileirar(
    override, description, monkeypatch
):
    mock_queue, _, _ = _setup_app_state()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=_make_usuario()),
    )
    mid = f"MSG_FILTRO_{description[:8].replace(' ', '_')}"
    payload = _make_payload(message_id=mid, **override)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200, f"falhou para caso: {description}"
    mock_queue.put.assert_not_awaited()


async def test_numero_nao_cadastrado_retorna_200_sem_enfileirar(monkeypatch):
    """Substitui o antigo filtro WHATSAPP_ALLOWED_NUMBER: numero desconhecido → discard."""
    mock_queue, _, _ = _setup_app_state()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=None),
    )
    payload = _make_payload(number="5511000000000", message_id="MSG_NAO_CADASTRADO_WW")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_queue.put.assert_not_awaited()


async def test_usuario_inativo_retorna_200_sem_enfileirar(monkeypatch):
    """Usuário inativo: buscar_por_telefone retorna None → discard."""
    mock_queue, _, _ = _setup_app_state()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=None),
    )
    payload = _make_payload(number=NUMERO, message_id="MSG_INATIVO_WW")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/webhook/mensagem",
            json=payload,
            headers={"apikey": VALID_APIKEY},
        )

    assert response.status_code == 200
    mock_queue.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Dedup por message_id
# ---------------------------------------------------------------------------


async def test_message_id_duplicado_enfileirado_apenas_uma_vez(monkeypatch):
    mock_queue, _, _ = _setup_app_state()
    usuario = _make_usuario()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=usuario),
    )
    payload = _make_payload(message_id="MSG_DEDUP_WW_001")

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
    assert mock_queue.put.await_count == 1


async def test_message_ids_distintos_sao_ambos_enfileirados(monkeypatch):
    mock_queue, _, _ = _setup_app_state()
    usuario = _make_usuario()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=usuario),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r1 = await client.post(
            "/webhook/mensagem",
            json=_make_payload(message_id="MSG_WW_A"),
            headers={"apikey": VALID_APIKEY},
        )
        r2 = await client.post(
            "/webhook/mensagem",
            json=_make_payload(message_id="MSG_WW_B"),
            headers={"apikey": VALID_APIKEY},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert mock_queue.put.await_count == 2


# ---------------------------------------------------------------------------
# Proteção de PII: payload NÃO logado em INFO
# ---------------------------------------------------------------------------


async def test_payload_completo_nao_logado_em_info(caplog, monkeypatch):
    _setup_app_state()
    usuario = _make_usuario()
    monkeypatch.setattr(
        "agent.entrypoint.webhook.resolver_usuario_por_telefone",
        AsyncMock(return_value=usuario),
    )
    payload = _make_payload(text="meu salario secreto", message_id="MSG_PII_WW_001")

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
    texto_usuario = "meu salario secreto"
    numero_usuario = NUMERO
    for record in caplog.records:
        if record.levelno == logging.INFO and "webhook recebido" in record.getMessage():
            assert texto_usuario not in record.getMessage()
            assert numero_usuario not in record.getMessage()
