import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from backend.auth import jwt as jwt_module
from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.auth.hashing import verificar_senha

router = APIRouter(prefix="/auth")

ERRO_CREDENCIAIS = {"erro": "credenciais inválidas"}
ERRO_REFRESH = {"erro": "refresh inválido"}


def _usuario_repo(session):
    from backend.repositories.usuario_repository import UsuarioRepository

    return UsuarioRepository(session)


def _store(request: Request):
    return request.app.state.refresh_store


def _abrir_sessao(request: Request):
    return request.app.state.sessionmaker()


def _role_valor(usuario) -> str:
    role = usuario.role
    return role.value if hasattr(role, "value") else str(role)


def _exp_datetime(payload: dict) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(payload["exp"], tz=datetime.timezone.utc)


async def _corpo(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


def _emitir_par(request: Request, usuario_id: int, role: str, email: str) -> dict:
    access = jwt_module.emitir_access(usuario_id=usuario_id, role=role, email=email)
    refresh, jti = jwt_module.emitir_refresh(usuario_id=usuario_id)
    payload = jwt_module.validar_refresh(refresh)
    _store(request).registrar(jti, _exp_datetime(payload))
    return {"access_token": access, "refresh_token": refresh}


@router.post("/login")
async def login(request: Request):
    body = await _corpo(request)
    email = body.get("email")
    senha = body.get("senha")
    if not email or not senha:
        return JSONResponse(ERRO_CREDENCIAIS, status_code=401)

    email = email.strip().lower()
    async with _abrir_sessao(request) as session:
        usuario = await _usuario_repo(session).buscar_por_email(email)

    if usuario is None or not usuario.ativo:
        return JSONResponse(ERRO_CREDENCIAIS, status_code=401)
    if not verificar_senha(senha, usuario.senha_hash):
        return JSONResponse(ERRO_CREDENCIAIS, status_code=401)

    role = _role_valor(usuario)
    par = _emitir_par(request, usuario.id, role, usuario.email)
    return {**par, "token_type": "bearer", "role": role}


@router.post("/refresh")
async def refresh(request: Request):
    body = await _corpo(request)
    token = body.get("refresh_token")
    if not token:
        return JSONResponse(ERRO_REFRESH, status_code=401)

    try:
        payload = jwt_module.validar_refresh(token)
    except jwt_module.TokenInvalido:
        return JSONResponse(ERRO_REFRESH, status_code=401)

    store = _store(request)
    jti = payload["jti"]
    if not store.ativo(jti):
        return JSONResponse(ERRO_REFRESH, status_code=401)

    usuario_id = int(payload["sub"])
    async with _abrir_sessao(request) as session:
        usuario = await _usuario_repo(session).buscar_por_id(usuario_id)

    if usuario is None or not usuario.ativo:
        return JSONResponse(ERRO_REFRESH, status_code=401)

    store.revogar(jti)
    par = _emitir_par(request, usuario_id, _role_valor(usuario), usuario.email)
    return {
        "access_token": par["access_token"],
        "refresh_token": par["refresh_token"],
        "token_type": "bearer",
    }


@router.get("/identidade/por-telefone/{telefone}")
async def identidade_por_telefone(
    telefone: str,
    request: Request,
    _usuario: UsuarioToken = Depends(get_usuario_atual),
):
    from backend.dtos.usuario import UsuarioResponse

    async with _abrir_sessao(request) as session:
        usuario = await _usuario_repo(session).buscar_por_telefone(telefone)

    if usuario is None:
        return Response(status_code=204)
    return UsuarioResponse.de_modelo(usuario).model_dump()


@router.post("/logout")
async def logout(request: Request):
    body = await _corpo(request)
    token = body.get("refresh_token")
    if token:
        try:
            payload = jwt_module.validar_refresh(token)
            _store(request).revogar(payload["jti"])
        except jwt_module.TokenInvalido:
            pass
    return {"ok": True}
