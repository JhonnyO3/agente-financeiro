from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.cartao import Cartao


class CartaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def listar(self, usuario_id: int) -> list[Cartao]:
        stmt = (
            select(Cartao)
            .where(Cartao.usuario_id == usuario_id)
            .order_by(Cartao.criado_em, Cartao.id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def buscar_por_id(self, id: int, usuario_id: int) -> Cartao | None:
        stmt = select(Cartao).where(
            Cartao.id == id, Cartao.usuario_id == usuario_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def criar(self, cartao: Cartao) -> Cartao:
        self._session.add(cartao)
        await self._session.flush()
        await self._session.refresh(cartao)
        return cartao

    async def atualizar(self, cartao: Cartao) -> Cartao:
        await self._session.flush()
        await self._session.refresh(cartao)
        return cartao

    async def excluir(self, id: int, usuario_id: int) -> None:
        stmt = delete(Cartao).where(
            Cartao.id == id, Cartao.usuario_id == usuario_id
        )
        await self._session.execute(stmt)
        await self._session.flush()
