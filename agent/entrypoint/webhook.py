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


def _normalizar_numero(numero: str) -> str:
    # Evolution API envia com DDI (ex: 5511999999999).
    # Se o número tiver mais de 11 dígitos e começar com "55", remove o DDI
    # para bater com o formato armazenado no banco (sem DDI).
    digitos = "".join(ch for ch in numero if ch.isdigit())
    if len(digitos) > 11 and digitos.startswith("55"):
        return digitos[2:]
    return digitos


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

    event = payload.get("event")
    if event != "messages.upsert":
        logger.debug("webhook ignorado event=%r (esperado messages.upsert)", event)
        return JSONResponse(status_code=200, content={"status": "ok"})

    numero_raw = extrair_numero(payload)
    numero = _normalizar_numero(numero_raw)
    from_me = payload.get("data", {}).get("key", {}).get("fromMe", False)
    logger.info("webhook recebido numero_raw=%r numero=%r from_me=%s", numero_raw, numero, from_me)

    texto = extrair_texto(payload)
    if not texto:
        msg_keys = list(payload.get("data", {}).get("message", {}).keys())
        logger.info("webhook ignorado sem texto numero=%r message_keys=%s", numero_raw, msg_keys)
        return JSONResponse(status_code=200, content={"status": "ok"})

    # Dedup por message_id
    message_id = extrair_message_id(payload)
    _poda_dedup()
    if message_id and message_id in _seen:
        logger.info("webhook dedup ignorado id=%s numero=%r", message_id, numero)
        return JSONResponse(status_code=200, content={"status": "ok"})

    if message_id:
        _seen[message_id] = time.monotonic()

    # Resolução de identidade in-process
    usuario = await resolver_usuario_por_telefone(request.app.state, numero)
    if usuario is None:
        logger.warning("webhook usuario nao encontrado numero=%r — verifique se o numero esta cadastrado no banco", numero)
        return JSONResponse(status_code=200, content={"status": "ok"})

    logger.info("webhook enfileirando numero=%r usuario_id=%s texto=%r", numero, usuario.id, texto[:80])
    await request.app.state.fila.put((usuario.id, numero, texto))
    return JSONResponse(status_code=200, content={"status": "ok"})
