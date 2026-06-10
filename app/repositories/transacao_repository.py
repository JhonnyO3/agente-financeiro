from dataclasses import asdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transacao import Transacao
from app.repositories.dtos import AgregadoCategoria, TransacaoCreate, TransacaoUpdate


class TransacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(self, transacao: TransacaoCreate) -> Transacao:
        obj = Transacao(
            tipo=transacao.tipo,
            valor=transacao.valor,
            descricao=transacao.descricao,
            categoria=transacao.categoria,
            data=transacao.data,
            parcela_numero=transacao.parcela_numero,
            parcela_total=transacao.parcela_total,
            grupo_parcela_id=str(transacao.grupo_parcela_id),
            embedding=transacao.embedding,
        )
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def criar_lote(self, transacoes: list[TransacaoCreate]) -> list[Transacao]:
        objetos = [
            Transacao(
                tipo=t.tipo,
                valor=t.valor,
                descricao=t.descricao,
                categoria=t.categoria,
                data=t.data,
                parcela_numero=t.parcela_numero,
                parcela_total=t.parcela_total,
                grupo_parcela_id=str(t.grupo_parcela_id),
                embedding=t.embedding,
            )
            for t in transacoes
        ]
        self._session.add_all(objetos)
        await self._session.flush()
        for obj in objetos:
            await self._session.refresh(obj)
        return objetos

    async def buscar_por_id(self, id: int) -> Transacao | None:
        result = await self._session.execute(select(Transacao).where(Transacao.id == id))
        return result.scalar_one_or_none()

    async def buscar_por_grupo(self, grupo_parcela_id: UUID) -> list[Transacao]:
        result = await self._session.execute(
            select(Transacao)
            .where(Transacao.grupo_parcela_id == str(grupo_parcela_id))
            .order_by(Transacao.parcela_numero)
        )
        return list(result.scalars().all())

    async def buscar_semantico(self, embedding: list[float], limite: int = 5) -> list[Transacao]:
        result = await self._session.execute(
            select(Transacao)
            .order_by(Transacao.embedding.l2_distance(embedding))
            .limit(limite)
        )
        return list(result.scalars().all())

    async def buscar_semantico_com_distancia(
        self, embedding: list[float], limite: int = 1
    ) -> tuple[Transacao, float] | None:
        distancia = Transacao.embedding.l2_distance(embedding).label("distancia")
        result = await self._session.execute(
            select(Transacao, distancia)
            .order_by(distancia)
            .limit(limite)
        )
        row = result.first()
        if row is None:
            return None
        transacao, dist = row
        return (transacao, float(dist))

    async def atualizar(self, id: int, dados: TransacaoUpdate) -> Transacao:
        obj = await self.buscar_por_id(id)
        campos = {k: v for k, v in asdict(dados).items() if v is not None}
        for campo, valor in campos.items():
            setattr(obj, campo, valor)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def excluir(self, id: int) -> None:
        await self._session.execute(delete(Transacao).where(Transacao.id == id))
        await self._session.flush()

    async def excluir_grupo(self, grupo_parcela_id: UUID) -> int:
        result = await self._session.execute(
            delete(Transacao).where(Transacao.grupo_parcela_id == str(grupo_parcela_id))
        )
        await self._session.flush()
        return result.rowcount

    async def listar_por_periodo(self, inicio: date, fim: date) -> list[Transacao]:
        result = await self._session.execute(
            select(Transacao)
            .where(Transacao.data.between(inicio, fim))
            .order_by(Transacao.data)
        )
        return list(result.scalars().all())

    async def agregar_por_categoria(self, inicio: date, fim: date) -> list[AgregadoCategoria]:
        result = await self._session.execute(
            select(
                Transacao.categoria,
                func.sum(Transacao.valor),
                func.count(),
            )
            .where(Transacao.data.between(inicio, fim))
            .group_by(Transacao.categoria)
        )
        return [
            AgregadoCategoria(
                categoria=row[0],
                total=Decimal(str(row[1])),
                quantidade=row[2],
            )
            for row in result.all()
        ]
