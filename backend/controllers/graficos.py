from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.transacao_repository import TransacaoRepository
from backend.dependencies import get_session
from backend.dtos.graficos import EvolucaoMes
from backend.services.graficos import GraficosService

router = APIRouter(prefix="/api/grafico")


@router.get("/mensal")
async def mensal(session: AsyncSession = Depends(get_session)) -> list[dict]:
    service = GraficosService(TransacaoRepository(session))
    return await service.mensal(date.today())


@router.get("/evolucao")
async def evolucao(session: AsyncSession = Depends(get_session)) -> list[EvolucaoMes]:
    service = GraficosService(TransacaoRepository(session))
    return await service.evolucao(date.today())
