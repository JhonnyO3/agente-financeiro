from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.controllers.util import corpo_json
from backend.dependencies import get_session, get_session_begin
from backend.services import transacoes as service

router = APIRouter(prefix="/api")


@router.get("/transacoes")
async def listar_transacoes(
    request: Request,
    periodo: str = "mes_atual",
    tipo: str | None = None,
    categoria: str | None = None,
    status: str | None = None,
    forma_pagamento: str | None = None,
    ordenar: str | None = None,
    direcao: str = "desc",
    pagina: int = 1,
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    return await service.listar(
        session,
        usuario.usuario_id,
        periodo,
        tipo,
        categoria,
        status,
        pagina or 1,
        forma_pagamento,
        ordenar,
        direcao,
    )


@router.post("/transacoes")
async def criar_transacao(
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await corpo_json(request)
    try:
        resultado = await service.criar(session, usuario.usuario_id, body)
    except service.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    return JSONResponse(resultado, status_code=201)


@router.put("/transacoes/{id}")
async def atualizar_transacao(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    body = await corpo_json(request)
    try:
        return await service.atualizar(session, usuario.usuario_id, id, body)
    except service.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    except service.NaoEncontradaError:
        return JSONResponse(
            {"erro": service.ERRO_NAO_ENCONTRADA}, status_code=404
        )


@router.delete("/transacoes/{id}")
async def excluir_transacao(
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
