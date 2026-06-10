"""Blueprint da API CRUD de transações (T05 — RF-07, RF-08).

Contratos: db-session.md, periodo.md, api-json.md, repository-reuse.md.
"""

import math
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from flask import Blueprint, jsonify, request

from app.models.enums import CategoriaEnum, TipoEnum
from app.repositories.dtos import TransacaoCreate, TransacaoUpdate
from app.repositories.transacao_repository import TransacaoRepository
from dashboard.db import SessionFactory
from dashboard.periodo import resolver_periodo

bp = Blueprint("api_transacoes", __name__, url_prefix="/api")

POR_PAGINA = 25

_ERRO_NAO_ENCONTRADA = {"erro": "Transacao nao encontrada"}


def serializar(t) -> dict:
    return {
        "id": t.id,
        "data": t.data.isoformat(),
        "descricao": t.descricao or "",
        "categoria": t.categoria if isinstance(t.categoria, str) else t.categoria.value,
        "valor": str(t.valor.quantize(Decimal("0.01"))),
        "parcela_numero": t.parcela_numero,
        "parcela_total": t.parcela_total,
        "tipo": t.tipo if isinstance(t.tipo, str) else t.tipo.value,
        "grupo_parcela_id": t.grupo_parcela_id,
    }


def _como_str(campo) -> str:
    """Campos do ORM podem chegar como str ou enum — compara por valor string."""
    return campo if isinstance(campo, str) else campo.value


@bp.get("/transacoes")
async def listar_transacoes():
    periodo = request.args.get("periodo", "mes_atual")
    tipo = request.args.get("tipo")
    categoria = request.args.get("categoria")
    pagina = request.args.get("pagina", default=1, type=int) or 1

    inicio, fim = resolver_periodo(periodo)

    async with SessionFactory() as session:
        repo = TransacaoRepository(session)
        transacoes = await repo.listar_por_periodo(inicio, fim)

    filtrada = [
        t
        for t in transacoes
        if (tipo is None or _como_str(t.tipo) == tipo)
        and (categoria is None or _como_str(t.categoria) == categoria)
    ]
    filtrada.sort(key=lambda t: (t.data, t.id), reverse=True)

    total = len(filtrada)
    paginas = math.ceil(total / POR_PAGINA)
    itens = filtrada[(pagina - 1) * POR_PAGINA : pagina * POR_PAGINA]

    return jsonify(
        {
            "itens": [serializar(t) for t in itens],
            "total": total,
            "pagina": pagina,
            "paginas": paginas,
            "por_pagina": POR_PAGINA,
        }
    )


@bp.post("/transacoes")
async def criar_transacao():
    body = request.get_json(silent=True) or {}

    faltando = [
        campo
        for campo in ("data", "valor", "tipo", "categoria")
        if body.get(campo) in (None, "")
    ]
    if faltando:
        return (
            jsonify({"erro": f"Campos obrigatorios ausentes: {', '.join(faltando)}"}),
            400,
        )

    try:
        tipo = TipoEnum(body["tipo"])
        categoria = CategoriaEnum(body["categoria"])
        valor = Decimal(str(body["valor"]))
        data = date.fromisoformat(body["data"])
    except (ValueError, TypeError, InvalidOperation):
        return jsonify({"erro": "Campos invalidos: verifique data, valor, tipo e categoria"}), 400

    transacao = TransacaoCreate(
        tipo=tipo,
        valor=valor,
        descricao=body.get("descricao"),
        categoria=categoria,
        data=data,
        parcela_numero=1,
        parcela_total=1,
        grupo_parcela_id=uuid4(),
        embedding=None,
    )

    async with SessionFactory.begin() as session:
        repo = TransacaoRepository(session)
        novo = await repo.criar(transacao)
        return jsonify({"id": novo.id, "ok": True}), 201


@bp.put("/transacoes/<int:id>")
async def atualizar_transacao(id: int):
    body = request.get_json(silent=True) or {}

    campos = {}
    try:
        if "data" in body:
            campos["data"] = date.fromisoformat(body["data"])
        if "descricao" in body:
            campos["descricao"] = body["descricao"]
        if "categoria" in body:
            campos["categoria"] = CategoriaEnum(body["categoria"])
        if "valor" in body:
            campos["valor"] = Decimal(str(body["valor"]))
    except (ValueError, TypeError, InvalidOperation):
        return jsonify({"erro": "Campos invalidos: verifique data, valor e categoria"}), 400

    async with SessionFactory.begin() as session:
        repo = TransacaoRepository(session)
        # `atualizar` no repository nao trata id inexistente — o buscar previo
        # na mesma sessao e obrigatorio.
        if await repo.buscar_por_id(id) is None:
            return jsonify(_ERRO_NAO_ENCONTRADA), 404
        await repo.atualizar(id, TransacaoUpdate(**campos))

    return jsonify({"ok": True})


@bp.delete("/transacoes/<int:id>")
async def excluir_transacao(id: int):
    async with SessionFactory.begin() as session:
        repo = TransacaoRepository(session)
        if await repo.buscar_por_id(id) is None:
            return jsonify(_ERRO_NAO_ENCONTRADA), 404
        await repo.excluir(id)

    return jsonify({"ok": True})
