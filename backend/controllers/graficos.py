from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.repositories.transacao_repository import TransacaoRepository
from backend.dependencies import get_session
from backend.dtos.graficos import EvolucaoMes
from backend.services.graficos import GraficosService

router = APIRouter(prefix="/api/grafico")


@router.get("/mensal")
async def mensal(
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
) -> list[dict]:
    service = GraficosService(TransacaoRepository(session))
    return await service.mensal(date.today(), usuario.usuario_id)


@router.get("/evolucao")
async def evolucao(
    session: AsyncSession = Depends(get_session),
    usuario: UsuarioToken = Depends(get_usuario_atual),
) -> list[EvolucaoMes]:
    service = GraficosService(TransacaoRepository(session))
    return await service.evolucao(date.today(), usuario.usuario_id)
