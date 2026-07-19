import decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.preferencias import Preferencias


class PreferenciasRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obter(self, usuario_id: int) -> Preferencias | None:
        result = await self._session.execute(
            select(Preferencias).where(Preferencias.usuario_id == usuario_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        usuario_id: int,
        renda_mensal: decimal.Decimal | None,
        metas: dict,
    ) -> Preferencias:
        obj = await self.obter(usuario_id)
        if obj is None:
            obj = Preferencias(
                usuario_id=usuario_id,
                renda_mensal=renda_mensal,
                metas=metas,
            )
            self._session.add(obj)
        else:
            obj.renda_mensal = renda_mensal
            obj.metas = metas
            obj.atualizado_em = func.now()
        await self._session.flush()
        await self._session.refresh(obj)
        return obj
