from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session, get_session_begin
from backend.dtos.recorrencia import RecorrenciaCreate, RecorrenciaUpdate
from backend.services import recorrencias as service

router = APIRouter(prefix="/api")

ERRO_BODY_INVALIDO = "dados invalidos"


async def _corpo(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@router.get("/recorrencias")
async def listar_recorrencias(
    ativo: bool | None = None,
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    return await service.listar(session, usuario.usuario_id, ativo=ativo)


@router.post("/recorrencias")
async def criar_recorrencia(
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await _corpo(request)
    try:
        dados = RecorrenciaCreate(**body)
    except ValidationError:
        return JSONResponse({"erro": ERRO_BODY_INVALIDO}, status_code=422)
    resultado = await service.criar(session, usuario.usuario_id, dados)
    return JSONResponse(resultado, status_code=201)


@router.put("/recorrencias/{id}")
async def atualizar_recorrencia(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await _corpo(request)
    try:
        dados = RecorrenciaUpdate(**body)
    except ValidationError:
        return JSONResponse({"erro": ERRO_BODY_INVALIDO}, status_code=422)
    try:
        return await service.atualizar(session, usuario.usuario_id, id, dados)
    except service.NaoEncontradaError:
        return JSONResponse(
            {"erro": service.ERRO_NAO_ENCONTRADA}, status_code=404
        )


@router.delete("/recorrencias/{id}")
async def excluir_recorrencia(
    id: int,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    try:
        return await service.excluir(session, usuario.usuario_id, id)
    except service.NaoEncontradaError:
        return JSONResponse(
            {"erro": service.ERRO_NAO_ENCONTRADA}, status_code=404
        )


@router.post("/recorrencias/materializar")
async def materializar_recorrencias(
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    gerados = await service.garantir_janela(
        session, usuario.usuario_id, date.today()
    )
    return {"gerados": gerados}
