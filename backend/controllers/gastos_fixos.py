from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session, get_session_begin
from backend.services import gastos_fixos as service

router = APIRouter(prefix="/api")


async def _corpo(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@router.get("/gastos-fixos")
async def listar_gastos_fixos(
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    return await service.listar(session, usuario.usuario_id)


@router.post("/gastos-fixos")
async def criar_gasto_fixo(
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await _corpo(request)
    try:
        resultado = await service.criar(session, usuario.usuario_id, body)
    except service.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    return JSONResponse(resultado, status_code=201)


@router.put("/gastos-fixos/{id}")
async def atualizar_gasto_fixo(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await _corpo(request)
    try:
        resultado = await service.atualizar(session, usuario.usuario_id, id, body)
    except service.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    except service.NaoEncontradaError:
        return JSONResponse({"erro": "Gasto fixo nao encontrado"}, status_code=404)
    return JSONResponse(resultado, status_code=200)


@router.delete("/gastos-fixos/{id}")
async def excluir_gasto_fixo(
    id: int,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    try:
        resultado = await service.excluir(session, usuario.usuario_id, id)
    except service.NaoEncontradaError:
        return JSONResponse({"erro": "Gasto fixo nao encontrado"}, status_code=404)
    return JSONResponse(resultado, status_code=200)
