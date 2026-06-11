from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session, get_session_begin
from backend.services import parcelas as service

router = APIRouter(prefix="/api")


@router.get("/parcelas-ativas")
async def parcelas_ativas(
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    return await service.listar_ativas(session, usuario.usuario_id)


@router.delete("/grupos/{grupo_parcela_id}")
async def excluir_grupo(
    grupo_parcela_id: str,
    session: AsyncSession = Depends(get_session_begin),
    usuario: UsuarioToken = Depends(get_usuario_atual),
):
    try:
        return await service.excluir_grupo(
            session, usuario.usuario_id, grupo_parcela_id
        )
    except service.IdInvalidoError:
        return JSONResponse({"erro": "ID inválido"}, status_code=400)
    except service.GrupoNaoEncontradoError:
        return JSONResponse({"erro": "Grupo nao encontrado"}, status_code=404)
