"""Blueprint da API de parcelas ativas (T04 — RF-06).

Endpoints:
- GET /api/parcelas-ativas — grupos parcelados com parcela futura
- DELETE /api/grupos/<grupo_parcela_id> — exclui o grupo inteiro

Contratos: db-session.md, api-json.md, repository-reuse.md (congelados).
"""

from datetime import date
from decimal import Decimal
from uuid import UUID

from flask import Blueprint, jsonify

from app.repositories.transacao_repository import TransacaoRepository
from dashboard.db import SessionFactory

bp = Blueprint("api_parcelas", __name__, url_prefix="/api")

# Range futuro amplo definido no contrato repository-reuse.md
_DATA_TETO = date(2030, 12, 31)


@bp.get("/parcelas-ativas")
async def parcelas_ativas():
    async with SessionFactory() as session:
        repo = TransacaoRepository(session)
        transacoes = await repo.listar_por_periodo(date.today(), _DATA_TETO)

    grupos: dict[str, list] = {}
    for transacao in transacoes:
        if transacao.parcela_total > 1:
            grupos.setdefault(transacao.grupo_parcela_id, []).append(transacao)

    itens = []
    for grupo_id, parcelas in grupos.items():
        # Entre as parcelas futuras, a de menor número é a próxima pendente
        proxima = min(parcelas, key=lambda p: p.parcela_numero)
        itens.append(
            {
                "grupo_parcela_id": grupo_id,
                "descricao": proxima.descricao,
                "valor_parcela": str(proxima.valor.quantize(Decimal("0.01"))),
                "parcela_numero": proxima.parcela_numero,
                "parcela_total": proxima.parcela_total,
                "proxima_data": proxima.data.isoformat(),
                "pagas": proxima.parcela_numero - 1,
            }
        )

    itens.sort(key=lambda item: item["proxima_data"])
    return jsonify(itens)


@bp.delete("/grupos/<grupo_parcela_id>")
async def excluir_grupo(grupo_parcela_id: str):
    try:
        gid = UUID(grupo_parcela_id)
    except ValueError:
        return jsonify({"erro": "ID inválido"}), 400

    async with SessionFactory.begin() as session:
        repo = TransacaoRepository(session)
        removidos = await repo.excluir_grupo(gid)

    if removidos == 0:
        return jsonify({"erro": "Grupo nao encontrado"}), 404
    return jsonify({"ok": True, "removidos": removidos})
