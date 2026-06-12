from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session_begin
from backend.services import grupos as service

router = APIRouter(prefix="/api")


async def _corpo(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@router.put("/grupos/{grupo_parcela_id}")
async def editar_grupo(
    grupo_parcela_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await _corpo(request)
    try:
        resultado = await service.editar_grupo(
            session, usuario.usuario_id, grupo_parcela_id, body
        )
    except service.IdInvalidoError:
        return JSONResponse({"erro": "ID inválido"}, status_code=400)
    except service.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    except service.GrupoNaoEncontradoError:
        return JSONResponse({"erro": "Grupo nao encontrado"}, status_code=404)
    return JSONResponse(resultado, status_code=200)


@router.post("/grupos")
async def criar_grupo(
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await _corpo(request)
    try:
        resultado = await service.criar_grupo(session, usuario.usuario_id, body)
    except service.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    return JSONResponse(resultado, status_code=201)
