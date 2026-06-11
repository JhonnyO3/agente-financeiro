from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_session
from backend.services import resumo as service

router = APIRouter(prefix="/api")


@router.get("/resumo")
async def resumo(
    periodo: str = "mes_atual",
    session: AsyncSession = Depends(get_session),
):
    return await service.calcular_resumo(session, periodo)


@router.get("/grafico/categorias")
async def grafico_categorias(
    periodo: str = "mes_atual",
    session: AsyncSession = Depends(get_session),
):
    return await service.categorias_gasto(session, periodo)
