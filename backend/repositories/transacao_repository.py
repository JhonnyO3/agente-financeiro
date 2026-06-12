from dataclasses import asdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import undefer

from backend.models.transacao import Transacao
from backend.repositories.dtos import AgregadoCategoria, TransacaoCreate, TransacaoUpdate


class TransacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(self, transacao: TransacaoCreate) -> Transacao:
        obj = Transacao(
            usuario_id=transacao.usuario_id,
            tipo=transacao.tipo,
            valor=transacao.valor,
            descricao=transacao.descricao,
            categoria=transacao.categoria,
            data=transacao.data,
            parcela_numero=transacao.parcela_numero,
            parcela_total=transacao.parcela_total,
            grupo_parcela_id=str(transacao.grupo_parcela_id),
            embedding=transacao.embedding,
            status=transacao.status,
            forma_pagamento=transacao.forma_pagamento,
            recorrente=transacao.recorrente,
            responsavel=transacao.responsavel,
            detalhes=transacao.detalhes,
        )
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def criar_lote(self, transacoes: list[TransacaoCreate]) -> list[Transacao]:
        objetos = [
            Transacao(
                usuario_id=t.usuario_id,
                tipo=t.tipo,
                valor=t.valor,
                descricao=t.descricao,
                categoria=t.categoria,
                data=t.data,
                parcela_numero=t.parcela_numero,
                parcela_total=t.parcela_total,
                grupo_parcela_id=str(t.grupo_parcela_id),
                embedding=t.embedding,
                status=t.status,
                forma_pagamento=t.forma_pagamento,
                recorrente=t.recorrente,
                responsavel=t.responsavel,
                detalhes=t.detalhes,
            )
            for t in transacoes
        ]
        self._session.add_all(objetos)
        await self._session.flush()
        for obj in objetos:
            await self._session.refresh(obj)
        return objetos

    async def buscar_por_id(self, id: int, usuario_id: int | None = None) -> Transacao | None:
        stmt = select(Transacao).where(Transacao.id == id)
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def buscar_por_grupo(
        self, grupo_parcela_id: UUID, usuario_id: int | None = None
    ) -> list[Transacao]:
        stmt = (
            select(Transacao)
            .where(Transacao.grupo_parcela_id == str(grupo_parcela_id))
            .order_by(Transacao.parcela_numero)
        )
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def buscar_semantico(
        self, embedding: list[float], limite: int = 5, usuario_id: int | None = None
    ) -> list[Transacao]:
        stmt = (
            select(Transacao)
            .order_by(Transacao.embedding.l2_distance(embedding))
            .limit(limite)
        )
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def buscar_semantico_com_distancia(
        self, embedding: list[float], limite: int = 1, usuario_id: int | None = None
    ) -> tuple[Transacao, float] | None:
        distancia = Transacao.embedding.l2_distance(embedding).label("distancia")
        stmt = (
            select(Transacao, distancia)
            .order_by(distancia)
            .limit(limite)
        )
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return None
        transacao, dist = row
        return (transacao, float(dist))

    async def buscar_semantico_multiplos_com_distancia(
        self, embedding: list[float], limite: int = 5, usuario_id: int | None = None
    ) -> list[tuple[Transacao, float]]:
        distancia = Transacao.embedding.l2_distance(embedding).label("distancia")
        stmt = (
            select(Transacao, distancia)
            .order_by(distancia)
            .limit(limite)
        )
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return [(transacao, float(dist)) for transacao, dist in result.all()]

    async def atualizar(
        self, id: int, dados: TransacaoUpdate, usuario_id: int | None = None
    ) -> Transacao:
        obj = await self.buscar_por_id(id, usuario_id=usuario_id)
        campos = {k: v for k, v in asdict(dados).items() if v is not None}
        for campo, valor in campos.items():
            setattr(obj, campo, valor)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def excluir(self, id: int, usuario_id: int | None = None) -> None:
        stmt = delete(Transacao).where(Transacao.id == id)
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def excluir_grupo(self, grupo_parcela_id: UUID, usuario_id: int | None = None) -> int:
        stmt = delete(Transacao).where(Transacao.grupo_parcela_id == str(grupo_parcela_id))
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def excluir_por_filtros(
        self,
        inicio: date,
        fim: date,
        categoria: str | None = None,
        usuario_id: int | None = None,
    ) -> int:
        stmt = delete(Transacao).where(Transacao.data.between(inicio, fim))
        if categoria is not None:
            stmt = stmt.where(Transacao.categoria == categoria)
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def contar_por_filtros(
        self,
        inicio: date,
        fim: date,
        categoria: str | None = None,
        usuario_id: int | None = None,
    ) -> int:
        from sqlalchemy import func as sa_func
        stmt = select(sa_func.count()).select_from(Transacao).where(Transacao.data.between(inicio, fim))
        if categoria is not None:
            stmt = stmt.where(Transacao.categoria == categoria)
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def listar_por_periodo(
        self, inicio: date, fim: date, usuario_id: int | None = None
    ) -> list[Transacao]:
        stmt = (
            select(Transacao)
            .where(Transacao.data.between(inicio, fim))
            .order_by(Transacao.data)
        )
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def listar_por_periodo_com_embedding(
        self, inicio: date, fim: date, usuario_id: int | None = None
    ) -> list[Transacao]:
        stmt = (
            select(Transacao)
            .where(Transacao.data.between(inicio, fim))
            .order_by(Transacao.data)
            .options(undefer(Transacao.embedding))
        )
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def agregar_por_categoria(
        self, inicio: date, fim: date, usuario_id: int | None = None
    ) -> list[AgregadoCategoria]:
        stmt = (
            select(
                Transacao.categoria,
                func.sum(Transacao.valor),
                func.count(),
            )
            .where(Transacao.data.between(inicio, fim))
            .group_by(Transacao.categoria)
        )
        if usuario_id is not None:
            stmt = stmt.where(Transacao.usuario_id == usuario_id)
        result = await self._session.execute(stmt)
        return [
            AgregadoCategoria(
                categoria=row[0],
                total=Decimal(str(row[1])),
                quantidade=row[2],
            )
            for row in result.all()
        ]
