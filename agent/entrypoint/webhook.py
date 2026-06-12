import hmac
import logging
import os
import time
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from agent.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Dedup em memória: message_id → timestamp de recebimento
_DEDUP_TTL_S = 600  # 10 minutos
_seen: dict[str, float] = {}


def _allowed_number() -> str:
    """Lê WHATSAPP_ALLOWED_NUMBER do ambiente em tempo de execução (isolamento em testes)."""
    return os.environ.get("WHATSAPP_ALLOWED_NUMBER", settings.WHATSAPP_ALLOWED_NUMBER)


def _webhook_apikey() -> str:
    """Lê WEBHOOK_APIKEY do ambiente em tempo de execução (isolamento em testes)."""
    return os.environ.get("WEBHOOK_APIKEY", settings.WEBHOOK_APIKEY)


def _poda_dedup() -> None:
    agora = time.monotonic()
    expirados = [k for k, t in _seen.items() if agora - t > _DEDUP_TTL_S]
    for k in expirados:
        del _seen[k]


def extrair_numero(payload: dict) -> str:
    return payload.get("data", {}).get("key", {}).get("remoteJid", "").split("@")[0]


def extrair_texto(payload: dict) -> str | None:
    msg = payload.get("data", {}).get("message", {})
    return msg.get("conversation") or msg.get("extendedTextMessage", {}).get("text")


def extrair_message_id(payload: dict) -> str:
    return payload.get("data", {}).get("key", {}).get("id", "")


@router.post("/mensagem")
async def receber_mensagem(payload: dict, request: Request) -> JSONResponse:
    # Auth constant-time
    apikey = request.headers.get("apikey", "")
    if not hmac.compare_digest(apikey, _webhook_apikey()):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    # Filtros silenciosos
    if payload.get("event") != "messages.upsert":
        return JSONResponse(status_code=200, content={"status": "ok"})

    key = payload.get("data", {}).get("key", {})
    if key.get("fromMe"):
        return JSONResponse(status_code=200, content={"status": "ok"})

    numero = extrair_numero(payload)
    if numero != _allowed_number():
        return JSONResponse(status_code=200, content={"status": "ok"})

    texto = extrair_texto(payload)
    if not texto:
        return JSONResponse(status_code=200, content={"status": "ok"})

    # Dedup por message_id
    message_id = extrair_message_id(payload)
    _poda_dedup()
    if message_id and message_id in _seen:
        logger.debug("mensagem duplicada ignorada id=%s", message_id)
        return JSONResponse(status_code=200, content={"status": "ok"})
    if message_id:
        _seen[message_id] = time.monotonic()

    logger.debug("webhook enfileirando numero=%s", numero)
    await request.app.state.fila.put((numero, texto))
    return JSONResponse(status_code=200, content={"status": "ok"})
