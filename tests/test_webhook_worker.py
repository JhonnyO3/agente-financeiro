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


# ---------------------------------------------------------------------------
# Worker: debounce
# ---------------------------------------------------------------------------


async def test_debounce_agrupa_fragmentos_do_mesmo_usuario():
    """
    Dois textos chegam para o mesmo número dentro da janela de debounce →
    o Classificador (ou processador) deve receber os dois unidos por '\n'.
    Usa DEBOUNCE_SEGUNDOS=0 via injeção direta no worker.
    """
    from agent.entrypoint import worker as worker_module  # worker ainda não existe → ImportError esperado

    mock_classificador = AsyncMock()
    mock_classificador.classificar = AsyncMock(return_value=MagicMock(intencao="FORA_DE_ESCOPO", confianca="alta"))
    mock_roteador = AsyncMock()
    mock_roteador.rotear = AsyncMock(return_value=MagicMock(acao="conversar", status="concluido", dados={"resposta": "ok"}))
    mock_formatador = MagicMock()
    mock_formatador.formatar = MagicMock(return_value="ok formatado")
    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()

    # Cria o worker com debounce_segundos=0 para não dormir nos testes
    w = worker_module.Worker(
        classificador=mock_classificador,
        roteador=mock_roteador,
        formatador=mock_formatador,
        evolution_client=mock_evolution,
        estado_store=AsyncMock(),
        debounce_segundos=0,
    )

    await w.receber(AUTHORIZED_NUMBER, "gastei")
    await w.receber(AUTHORIZED_NUMBER, "30 no uber")
    await w.processar_pendentes()

    # O classificador deve ter sido chamado UMA vez com o texto unido
    mock_classificador.classificar.assert_awaited_once()
    texto_recebido = mock_classificador.classificar.await_args[0][0]
    assert texto_recebido == "gastei\n30 no uber", (
        f"Esperado 'gastei\\n30 no uber', recebido: {texto_recebido!r}"
    )


async def test_debounce_nao_mistura_usuarios_diferentes():
    """Fragmentos de usuários distintos não devem ser mesclados."""
    from agent.entrypoint import worker as worker_module

    chamadas: list[tuple[str, str]] = []

    async def fake_processar(numero: str, texto: str) -> None:
        chamadas.append((numero, texto))

    mock_classificador = AsyncMock()
    mock_classificador.classificar = AsyncMock(return_value=MagicMock(intencao="FORA_DE_ESCOPO", confianca="alta"))
    mock_roteador = AsyncMock()
    mock_roteador.rotear = AsyncMock(return_value=MagicMock(acao="conversar", status="concluido", dados={"resposta": "ok"}))
    mock_formatador = MagicMock()
    mock_formatador.formatar = MagicMock(return_value="ok")
    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()

    w = worker_module.Worker(
        classificador=mock_classificador,
        roteador=mock_roteador,
        formatador=mock_formatador,
        evolution_client=mock_evolution,
        estado_store=AsyncMock(),
        debounce_segundos=0,
    )

    await w.receber("5511111111111", "texto usuario A")
    await w.receber("5522222222222", "texto usuario B")
    await w.processar_pendentes()

    # Cada número deve ter sido processado separadamente
    assert mock_classificador.classificar.await_count == 2
    textos = [c[0][0] for c in mock_classificador.classificar.await_args_list]
    assert "texto usuario A" in textos
    assert "texto usuario B" in textos
    # Nenhum texto deve conter os dois juntos
    for t in textos:
        assert "texto usuario A" not in t or "texto usuario B" not in t


# ---------------------------------------------------------------------------
# Worker: fluxo feliz — chama Classificador → Roteador → Formatador → EvolutionClient
# ---------------------------------------------------------------------------


async def test_worker_fluxo_feliz_chama_pipeline_completo():
    from agent.entrypoint import worker as worker_module

    mock_intencao = MagicMock(intencao="CONSULTAR", confianca="alta")
    mock_resultado = MagicMock(acao="listar", status="concluido", dados={})
    resposta_formatada = "Aqui estão seus gastos!"

    mock_classificador = AsyncMock()
    mock_classificador.classificar = AsyncMock(return_value=mock_intencao)
    mock_roteador = AsyncMock()
    mock_roteador.rotear = AsyncMock(return_value=mock_resultado)
    mock_formatador = MagicMock()
    mock_formatador.formatar = MagicMock(return_value=resposta_formatada)
    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()
    mock_estado_store = AsyncMock()
    mock_estado_store.registrar_mensagem = AsyncMock()

    w = worker_module.Worker(
        classificador=mock_classificador,
        roteador=mock_roteador,
        formatador=mock_formatador,
        evolution_client=mock_evolution,
        estado_store=mock_estado_store,
        debounce_segundos=0,
    )

    await w.receber(AUTHORIZED_NUMBER, "listar gastos")
    await w.processar_pendentes()

    mock_classificador.classificar.assert_awaited_once_with("listar gastos")
    mock_roteador.rotear.assert_awaited_once()
    mock_formatador.formatar.assert_called_once_with(mock_resultado)
    mock_evolution.enviar_mensagem.assert_awaited_once_with(AUTHORIZED_NUMBER, resposta_formatada)


# ---------------------------------------------------------------------------
# Worker: registra histórico no estado_store
# ---------------------------------------------------------------------------


async def test_worker_registra_mensagem_usuario_e_assistente():
    from agent.entrypoint import worker as worker_module
    from agent.domain.estado import Mensagem

    resposta_assistente = "Resposta do bot"

    mock_classificador = AsyncMock()
    mock_classificador.classificar = AsyncMock(
        return_value=MagicMock(intencao="FORA_DE_ESCOPO", confianca="alta")
    )
    mock_roteador = AsyncMock()
    mock_roteador.rotear = AsyncMock(
        return_value=MagicMock(acao="conversar", status="concluido", dados={"resposta": resposta_assistente})
    )
    mock_formatador = MagicMock()
    mock_formatador.formatar = MagicMock(return_value=resposta_assistente)
    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()
    mock_estado_store = AsyncMock()
    mock_estado_store.registrar_mensagem = AsyncMock()

    w = worker_module.Worker(
        classificador=mock_classificador,
        roteador=mock_roteador,
        formatador=mock_formatador,
        evolution_client=mock_evolution,
        estado_store=mock_estado_store,
        debounce_segundos=0,
    )

    await w.receber(AUTHORIZED_NUMBER, "oi")
    await w.processar_pendentes()

    assert mock_estado_store.registrar_mensagem.await_count >= 2

    calls = mock_estado_store.registrar_mensagem.await_args_list
    papeis = [c.kwargs.get("msg", c.args[1] if len(c.args) > 1 else None) for c in calls]

    # Aceita tanto args posicionais quanto kwargs
    msgs_recebidas = []
    for c in calls:
        if c.args and len(c.args) > 1:
            msgs_recebidas.append(c.args[1])
        elif "msg" in c.kwargs:
            msgs_recebidas.append(c.kwargs["msg"])

    papeis_encontrados = {m.papel for m in msgs_recebidas if hasattr(m, "papel")}
    assert "usuario" in papeis_encontrados, "Mensagem do usuário não registrada no estado_store"
    assert "assistente" in papeis_encontrados, "Resposta do assistente não registrada no estado_store"


# ---------------------------------------------------------------------------
# Worker: exceção no processamento → mensagem amigável (nunca silêncio)
# ---------------------------------------------------------------------------


async def test_worker_excecao_envia_mensagem_amigavel():
    from agent.entrypoint import worker as worker_module

    mock_classificador = AsyncMock()
    mock_classificador.classificar = AsyncMock(side_effect=RuntimeError("falha inesperada"))
    mock_roteador = AsyncMock()
    mock_formatador = MagicMock()
    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()
    mock_estado_store = AsyncMock()

    w = worker_module.Worker(
        classificador=mock_classificador,
        roteador=mock_roteador,
        formatador=mock_formatador,
        evolution_client=mock_evolution,
        estado_store=mock_estado_store,
        debounce_segundos=0,
    )

    # Não deve propagar a exceção
    await w.receber(AUTHORIZED_NUMBER, "qualquer coisa")
    await w.processar_pendentes()  # não deve levantar

    # enviar_mensagem deve ter sido chamado com mensagem de erro amigável (não técnica)
    mock_evolution.enviar_mensagem.assert_awaited_once()
    args = mock_evolution.enviar_mensagem.await_args
    numero_enviado = args[0][0] if args[0] else args.kwargs.get("numero")
    mensagem_enviada = args[0][1] if args[0] else args.kwargs.get("mensagem")

    assert numero_enviado == AUTHORIZED_NUMBER
    assert isinstance(mensagem_enviada, str)
    assert len(mensagem_enviada) > 0
    # Mensagem amigável não deve expor stacktrace ou "RuntimeError"
    assert "RuntimeError" not in mensagem_enviada
    assert "Traceback" not in mensagem_enviada
