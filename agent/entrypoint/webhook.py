import logging
from fastapi import APIRouter, Request
from agent.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def extrair_numero(payload: dict) -> str:
    return payload.get("data", {}).get("key", {}).get("remoteJid", "").split("@")[0]


def extrair_texto(payload: dict) -> str | None:
    msg = payload.get("data", {}).get("message", {})
    return msg.get("conversation") or msg.get("extendedTextMessage", {}).get("text")


@router.post("/mensagem")
async def receber_mensagem(payload: dict, request: Request) -> dict:
    if payload.get("event") != "messages.upsert":
        return {"status": "ok"}
    if payload.get("data", {}).get("key", {}).get("fromMe"):
        return {"status": "ok"}
    logger.info("webhook recebido: %s", payload)
    numero = extrair_numero(payload)
    texto = extrair_texto(payload)
    logger.info("numero=%s texto=%s autorizado=%s", numero, texto, numero == settings.WHATSAPP_ALLOWED_NUMBER)
    if numero != settings.WHATSAPP_ALLOWED_NUMBER:
        return {"status": "ok"}
    if texto is None:
        return {"status": "ok"}
    await request.app.state.debouncer.receber(
        numero, texto, request.app.state.processar_e_responder
    )
    return {"status": "ok"}
