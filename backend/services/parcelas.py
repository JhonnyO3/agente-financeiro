from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.transacao_repository import TransacaoRepository

_DATA_TETO = date(2030, 12, 31)


class IdInvalidoError(Exception):
    pass


class GrupoNaoEncontradoError(Exception):
    pass


async def listar_ativas(session: AsyncSession) -> list[dict]:
    repo = TransacaoRepository(session)
    transacoes = await repo.listar_por_periodo(date.today(), _DATA_TETO)

    grupos: dict[str, list] = {}
    for transacao in transacoes:
        if transacao.parcela_total > 1:
            grupos.setdefault(transacao.grupo_parcela_id, []).append(transacao)

    itens = []
    for parcelas in grupos.values():
        proxima = min(parcelas, key=lambda p: p.parcela_numero)
        itens.append(
            {
                "grupo_parcela_id": proxima.grupo_parcela_id,
                "descricao": proxima.descricao,
                "valor_parcela": str(proxima.valor.quantize(Decimal("0.01"))),
                "parcela_numero": proxima.parcela_numero,
                "parcela_total": proxima.parcela_total,
                "proxima_data": proxima.data.isoformat(),
                "pagas": proxima.parcela_numero - 1,
            }
        )

    itens.sort(key=lambda item: item["proxima_data"])
    return itens


async def excluir_grupo(session: AsyncSession, grupo_parcela_id: str) -> dict:
    try:
        gid = UUID(grupo_parcela_id)
    except ValueError:
        raise IdInvalidoError("ID inválido")

    repo = TransacaoRepository(session)
    removidos = await repo.excluir_grupo(gid)
    if removidos == 0:
        raise GrupoNaoEncontradoError("Grupo nao encontrado")
    return {"ok": True, "removidos": removidos}
