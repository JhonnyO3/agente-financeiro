from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.transacao_repository import TransacaoRepository

_DATA_TETO = date(2030, 12, 31)


def _como_str(campo) -> str:
    return campo.value if hasattr(campo, "value") else campo


class IdInvalidoError(Exception):
    pass


class GrupoNaoEncontradoError(Exception):
    pass


async def listar_ativas(session: AsyncSession, usuario_id: int) -> list[dict]:
    repo = TransacaoRepository(session)
    transacoes = await repo.listar_por_periodo(
        date(2000, 1, 1), _DATA_TETO, usuario_id=usuario_id
    )

    grupos: dict[str, list] = {}
    for transacao in transacoes:
        if transacao.parcela_total > 1:
            grupos.setdefault(transacao.grupo_parcela_id, []).append(transacao)

    itens = []
    for parcelas in grupos.values():
        pendentes = [p for p in parcelas if _como_str(p.status) == "PENDENTE"]
        if not pendentes:
            continue
        proxima = min(pendentes, key=lambda p: p.parcela_numero)
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


async def excluir_grupo(
    session: AsyncSession, usuario_id: int, grupo_parcela_id: str
) -> dict:
    try:
        gid = UUID(grupo_parcela_id)
    except ValueError:
        raise IdInvalidoError("ID inválido")

    repo = TransacaoRepository(session)
    removidos = await repo.excluir_grupo(gid, usuario_id=usuario_id)
    if removidos == 0:
        raise GrupoNaoEncontradoError("Grupo nao encontrado")
    return {"ok": True, "removidos": removidos}
