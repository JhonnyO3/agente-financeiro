import datetime
import uuid

import jwt as pyjwt

from backend.config import settings

_ALGORITMO = "HS256"


class TokenInvalido(Exception):
    pass


def _agora() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def emitir_access(usuario_id: int, role: str, email: str) -> str:
    exp = _agora() + datetime.timedelta(minutes=settings.JWT_ACCESS_EXPIRES_MIN)
    payload = {
        "sub": str(usuario_id),
        "role": role,
        "email": email,
        "type": "access",
        "exp": exp,
    }
    return pyjwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITMO)


def emitir_refresh(usuario_id: int) -> tuple[str, str]:
    jti = str(uuid.uuid4())
    exp = _agora() + datetime.timedelta(days=settings.JWT_REFRESH_EXPIRES_DAYS)
    payload = {
        "sub": str(usuario_id),
        "type": "refresh",
        "jti": jti,
        "exp": exp,
    }
    token = pyjwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITMO)
    return token, jti


def _decodificar(token: str) -> dict:
    try:
        return pyjwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITMO])
    except pyjwt.PyJWTError as erro:
        raise TokenInvalido(str(erro)) from erro


def validar_access(token: str) -> dict:
    payload = _decodificar(token)
    if payload.get("type") != "access":
        raise TokenInvalido("type incorreto")
    return payload


def validar_refresh(token: str) -> dict:
    payload = _decodificar(token)
    if payload.get("type") != "refresh":
        raise TokenInvalido("type incorreto")
    return payload
