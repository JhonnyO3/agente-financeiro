from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.auth import jwt as jwt_module
from backend.config import settings
from backend.repositories.usuario_repository import UsuarioRepository


class HttpErro(Exception):
    def __init__(self, status: int, erro: str) -> None:
        self.status = status
        self.erro = erro


def instalar_handlers(app: FastAPI) -> None:
    @app.exception_handler(HttpErro)
    async def _handler(request: Request, exc: HttpErro) -> JSONResponse:
        return JSONResponse({"erro": exc.erro}, status_code=exc.status)


@dataclass
class UsuarioToken:
    usuario_id: int
    role: str
    email: str


def _extrair_bearer(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    prefixo = "Bearer "
    if not header.startswith(prefixo):
        raise HttpErro(401, "não autenticado")
    return header[len(prefixo):].strip()


async def get_usuario_atual(request: Request) -> UsuarioToken:
    token = _extrair_bearer(request)
    try:
        payload = jwt_module.validar_access(token)
    except jwt_module.TokenInvalido:
        raise HttpErro(401, "não autenticado")
    return UsuarioToken(
        usuario_id=int(payload["sub"]),
        role=payload["role"],
        email=payload["email"],
    )


def _abrir_sessao(request: Request):
    return request.app.state.sessionmaker()


def _role_valor(usuario) -> str:
    role = usuario.role
    return role.value if hasattr(role, "value") else str(role)


async def get_admin(request: Request) -> UsuarioToken:
    usuario = await get_usuario_atual(request)

    if usuario.role != "ADMIN":
        raise HttpErro(403, "acesso negado")
    if usuario.email.lower() not in settings.ADMIN_EMAILS:
        raise HttpErro(403, "acesso negado")

    async with _abrir_sessao(request) as session:
        repo = UsuarioRepository(session)
        registro = await repo.buscar_por_id(usuario.usuario_id)

    if registro is None or not registro.ativo or _role_valor(registro) != "ADMIN":
        raise HttpErro(403, "acesso negado")

    return usuario
