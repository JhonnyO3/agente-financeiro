from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import get_admin
from backend.dependencies import get_session, get_session_begin
from backend.dtos.usuario import UsuarioCreateRequest, UsuarioUpdateRequest
from backend.services import admin_transacoes, admin_usuarios

router = APIRouter(prefix="/admin", dependencies=[Depends(get_admin)])

ERRO_BODY_INVALIDO = "dados inválidos"


async def _corpo(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


@router.get("/usuarios")
async def listar_usuarios(session: AsyncSession = Depends(get_session)):
    return await admin_usuarios.listar(session)


@router.get("/usuarios/{id}")
async def obter_usuario(id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await admin_usuarios.obter(session, id)
    except admin_usuarios.NaoEncontradoError:
        return JSONResponse(
            {"erro": admin_usuarios.ERRO_NAO_ENCONTRADO}, status_code=404
        )


@router.post("/usuarios")
async def criar_usuario(
    request: Request, session: AsyncSession = Depends(get_session_begin)
):
    body = await _corpo(request)
    try:
        dados = UsuarioCreateRequest(**body)
    except ValidationError:
        return JSONResponse({"erro": ERRO_BODY_INVALIDO}, status_code=422)
    try:
        resultado = await admin_usuarios.criar(session, dados)
    except admin_usuarios.EmailDuplicadoError:
        return JSONResponse(
            {"erro": admin_usuarios.ERRO_EMAIL_DUPLICADO}, status_code=409
        )
    return JSONResponse(resultado, status_code=201)


@router.put("/usuarios/{id}")
async def atualizar_usuario(
    id: int, request: Request, session: AsyncSession = Depends(get_session_begin)
):
    body = await _corpo(request)
    try:
        dados = UsuarioUpdateRequest(**body)
    except ValidationError:
        return JSONResponse({"erro": ERRO_BODY_INVALIDO}, status_code=422)
    try:
        return await admin_usuarios.atualizar(session, id, dados)
    except admin_usuarios.NaoEncontradoError:
        return JSONResponse(
            {"erro": admin_usuarios.ERRO_NAO_ENCONTRADO}, status_code=404
        )
    except admin_usuarios.EmailDuplicadoError:
        return JSONResponse(
            {"erro": admin_usuarios.ERRO_EMAIL_DUPLICADO}, status_code=409
        )


@router.delete("/usuarios/{id}")
async def excluir_usuario(id: int, session: AsyncSession = Depends(get_session_begin)):
    try:
        return await admin_usuarios.excluir(session, id)
    except admin_usuarios.NaoEncontradoError:
        return JSONResponse(
            {"erro": admin_usuarios.ERRO_NAO_ENCONTRADO}, status_code=404
        )


@router.get("/usuarios/{usuario_id}/transacoes")
async def listar_transacoes(
    usuario_id: int, session: AsyncSession = Depends(get_session)
):
    return await admin_transacoes.listar(session, usuario_id)


@router.post("/usuarios/{usuario_id}/transacoes")
async def criar_transacao(
    usuario_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
):
    body = await _corpo(request)
    try:
        resultado = await admin_transacoes.criar(session, usuario_id, body)
    except admin_transacoes.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    return JSONResponse(resultado, status_code=201)


@router.get("/transacoes/{id}")
async def obter_transacao(id: int, session: AsyncSession = Depends(get_session)):
    try:
        return await admin_transacoes.obter(session, id)
    except admin_transacoes.NaoEncontradaError:
        return JSONResponse(
            {"erro": admin_transacoes.ERRO_NAO_ENCONTRADA}, status_code=404
        )


@router.put("/transacoes/{id}")
async def atualizar_transacao(
    id: int, request: Request, session: AsyncSession = Depends(get_session_begin)
):
    body = await _corpo(request)
    try:
        return await admin_transacoes.atualizar(session, id, body)
    except admin_transacoes.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    except admin_transacoes.NaoEncontradaError:
        return JSONResponse(
            {"erro": admin_transacoes.ERRO_NAO_ENCONTRADA}, status_code=404
        )


@router.delete("/transacoes/{id}")
async def excluir_transacao(
    id: int, session: AsyncSession = Depends(get_session_begin)
):
    try:
        return await admin_transacoes.excluir(session, id)
    except admin_transacoes.NaoEncontradaError:
        return JSONResponse(
            {"erro": admin_transacoes.ERRO_NAO_ENCONTRADA}, status_code=404
        )
