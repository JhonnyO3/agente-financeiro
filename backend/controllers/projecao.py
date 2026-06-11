from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.repositories.transacao_repository import TransacaoRepository
from backend.dependencies import get_session
from backend.dtos.graficos import ProjecaoMes
from backend.services.projecao import ProjecaoService

router = APIRouter(prefix="/api")


@router.get("/projecao")
async def projecao(
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
) -> list[ProjecaoMes]:
    service = ProjecaoService(TransacaoRepository(session))
    return await service.projecao(date.today(), usuario.usuario_id)
