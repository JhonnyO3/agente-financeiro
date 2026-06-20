import logging
import time
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.repositories.usuario_repository import UsuarioRepository

router = APIRouter()
logger = logging.getLogger(__name__)

# Dedup em memória: message_id → timestamp de recebimento
_DEDUP_TTL_S = 600  # 10 minutos
_seen: dict[str, float] = {}


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


async def resolver_usuario_por_telefone(app_state, numero: str):
    async with app_state.session_factory() as session:
        repo = UsuarioRepository(session)
        return await repo.buscar_por_telefone(numero)


@router.post("/mensagem")
async def receber_mensagem(payload: dict, request: Request) -> JSONResponse:

    # Filtros silenciosos
    if payload.get("event") != "messages.upsert":
        return JSONResponse(status_code=200, content={"status": "ok"})

    numero = extrair_numero(payload)

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

    # Resolução de identidade in-process
    usuario = await resolver_usuario_por_telefone(request.app.state, numero)
    if usuario is None:
        return JSONResponse(status_code=200, content={"status": "ok"})

    logger.debug("webhook enfileirando numero=%s usuario_id=%s", numero, usuario.id)
    await request.app.state.fila.put((usuario.id, numero, texto))
    return JSONResponse(status_code=200, content={"status": "ok"})
