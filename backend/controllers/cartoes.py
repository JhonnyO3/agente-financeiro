from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session, get_session_begin
from backend.services import cartoes as service

router = APIRouter(prefix="/api")


async def _corpo(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@router.get("/cartoes")
async def listar_cartoes(
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    return await service.listar(session, usuario.usuario_id)


@router.post("/cartoes")
async def criar_cartao(
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


@router.get("/cartoes/{id}/resumo")
async def resumo_cartao(
    id: int,
    periodo: str = "mes_atual",
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    try:
        return await service.resumo(session, usuario.usuario_id, id, periodo)
    except service.NaoEncontradoError:
        return JSONResponse(
            {"erro": service.ERRO_NAO_ENCONTRADO}, status_code=404
        )


@router.put("/cartoes/{id}")
async def atualizar_cartao(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await _corpo(request)
    try:
        return await service.atualizar(session, usuario.usuario_id, id, body)
    except service.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    except service.NaoEncontradoError:
        return JSONResponse(
            {"erro": service.ERRO_NAO_ENCONTRADO}, status_code=404
        )


@router.delete("/cartoes/{id}")
async def excluir_cartao(
    id: int,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    try:
        return await service.excluir(session, usuario.usuario_id, id)
    except service.NaoEncontradoError:
        return JSONResponse(
            {"erro": service.ERRO_NAO_ENCONTRADO}, status_code=404
        )
