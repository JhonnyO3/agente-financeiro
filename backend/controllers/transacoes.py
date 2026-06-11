from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_session, get_session_begin
from backend.services import transacoes as service

router = APIRouter(prefix="/api")


async def _corpo(request: Request) -> dict:
    try:
        body = await request.json()
    except Exception:
        return {}
    return body if isinstance(body, dict) else {}


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
):
    return await service.listar(
        session, periodo, tipo, categoria, status, pagina or 1, forma_pagamento, ordenar, direcao
    )


@router.post("/transacoes")
async def criar_transacao(
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
):
    body = await _corpo(request)
    try:
        resultado = await service.criar(session, body)
    except service.ValidacaoError as erro:
        return JSONResponse({"erro": erro.mensagem}, status_code=400)
    return JSONResponse(resultado, status_code=201)


@router.put("/transacoes/{id}")
async def atualizar_transacao(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_session_begin),
):
    body = await _corpo(request)
    try:
        return await service.atualizar(session, id, body)
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
):
    try:
        return await service.excluir(session, id)
    except service.NaoEncontradaError:
        return JSONResponse(
            {"erro": service.ERRO_NAO_ENCONTRADA}, status_code=404
        )
