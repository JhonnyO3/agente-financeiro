from fastapi import APIRouter
from app.config import settings
from app.entrypoint.debounce import MessageDebouncer

router = APIRouter()
debouncer = MessageDebouncer()


def extrair_numero(payload: dict) -> str:
    return payload.get("data", {}).get("key", {}).get("remoteJid", "").split("@")[0]


def extrair_texto(payload: dict) -> str | None:
    msg = payload.get("data", {}).get("message", {})
    return msg.get("conversation") or msg.get("extendedTextMessage", {}).get("text")


@router.post("/mensagem")
async def receber_mensagem(payload: dict) -> dict:
    numero = extrair_numero(payload)
    texto = extrair_texto(payload)
    if numero != settings.WHATSAPP_ALLOWED_NUMBER:
        return {"status": "ok"}
    if texto is None:
        return {"status": "ok"}
    await debouncer.receber(numero, texto, _pipeline_placeholder)
    return {"status": "ok"}


async def _pipeline_placeholder(numero: str, texto: str) -> None:
    pass
