from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_session, get_session_begin
from backend.services import parcelas as service

router = APIRouter(prefix="/api")


@router.get("/parcelas-ativas")
async def parcelas_ativas(session: AsyncSession = Depends(get_session)):
    return await service.listar_ativas(session)


@router.delete("/grupos/{grupo_parcela_id}")
async def excluir_grupo(
    grupo_parcela_id: str,
    session: AsyncSession = Depends(get_session_begin),
):
    try:
        return await service.excluir_grupo(session, grupo_parcela_id)
    except service.IdInvalidoError:
        return JSONResponse({"erro": "ID inválido"}, status_code=400)
    except service.GrupoNaoEncontradoError:
        return JSONResponse({"erro": "Grupo nao encontrado"}, status_code=404)
