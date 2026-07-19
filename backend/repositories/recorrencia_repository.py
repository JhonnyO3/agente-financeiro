import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.recorrencia import Recorrencia, RecorrenciaLancamento


class RecorrenciaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self,
        usuario_id: int,
        descricao: str,
        tipo: str,
        categoria: str,
        valor: Decimal,
        dia_vencimento: int | None = None,
        forma_pagamento: str | None = None,
        ativo: bool = True,
    ) -> Recorrencia:
        obj = Recorrencia(
            usuario_id=usuario_id,
            descricao=descricao,
            tipo=tipo,
            categoria=categoria,
            valor=valor,
            dia_vencimento=dia_vencimento,
            forma_pagamento=forma_pagamento,
            ativo=ativo,
        )
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def listar(
        self, usuario_id: int, ativo: bool | None = None
    ) -> list[Recorrencia]:
        stmt = select(Recorrencia).where(Recorrencia.usuario_id == usuario_id)
        if ativo is not None:
            stmt = stmt.where(Recorrencia.ativo == ativo)
        stmt = stmt.order_by(Recorrencia.id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def listar_ativas(self, usuario_id: int) -> list[Recorrencia]:
        return await self.listar(usuario_id, ativo=True)

    async def buscar_por_id(
        self, id: int, usuario_id: int | None = None
    ) -> Recorrencia | None:
        stmt = select(Recorrencia).where(Recorrencia.id == id)
        if usuario_id is not None:
            stmt = stmt.where(Recorrencia.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def atualizar(
        self, id: int, dados: dict, usuario_id: int | None = None
    ) -> Recorrencia:
        obj = await self.buscar_por_id(id, usuario_id=usuario_id)
        for campo, valor in dados.items():
            setattr(obj, campo, valor)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def excluir(self, id: int, usuario_id: int | None = None) -> None:
        obj = await self.buscar_por_id(id, usuario_id=usuario_id)
        if obj is not None:
            await self._session.delete(obj)
            await self._session.flush()

    async def existe_lancamento(
        self, recorrencia_id: int, competencia: datetime.date
    ) -> bool:
        stmt = select(RecorrenciaLancamento.id).where(
            RecorrenciaLancamento.recorrencia_id == recorrencia_id,
            RecorrenciaLancamento.competencia == competencia,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def registrar_lancamento(
        self,
        recorrencia_id: int,
        competencia: datetime.date,
        transacao_id: int | None = None,
    ) -> RecorrenciaLancamento:
        obj = RecorrenciaLancamento(
            recorrencia_id=recorrencia_id,
            competencia=competencia,
            transacao_id=transacao_id,
        )
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj
