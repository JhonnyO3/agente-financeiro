from fastapi import APIRouter, Request
from app.config import settings

router = APIRouter()


def extrair_numero(payload: dict) -> str:
    return payload.get("data", {}).get("key", {}).get("remoteJid", "").split("@")[0]


def extrair_texto(payload: dict) -> str | None:
    msg = payload.get("data", {}).get("message", {})
    return msg.get("conversation") or msg.get("extendedTextMessage", {}).get("text")


@router.post("/mensagem")
async def receber_mensagem(payload: dict, request: Request) -> dict:
    numero = extrair_numero(payload)
    texto = extrair_texto(payload)
    if numero != settings.WHATSAPP_ALLOWED_NUMBER:
        return {"status": "ok"}
    if texto is None:
        return {"status": "ok"}
    await request.app.state.debouncer.receber(
        numero, texto, request.app.state.processar_e_responder
    )
    return {"status": "ok"}
