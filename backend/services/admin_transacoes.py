from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.enums import CategoriaEnum, FormaPagamentoEnum, StatusEnum, TipoEnum
from backend.repositories.dtos import TransacaoCreate, TransacaoUpdate
from backend.repositories.transacao_repository import TransacaoRepository
from backend.services.transacoes import (
    NaoEncontradaError,
    ValidacaoError,
    _serializar,
)

ERRO_NAO_ENCONTRADA = "Transacao nao encontrada"


def _repo(session: AsyncSession) -> TransacaoRepository:
    return TransacaoRepository(session)


async def listar(session: AsyncSession, usuario_id: int) -> list[dict]:
    repo = _repo(session)
    transacoes = await repo.listar_por_periodo(
        date.min, date.max, usuario_id=usuario_id
    )
    transacoes = sorted(transacoes, key=lambda t: (t.data, t.id), reverse=True)
    return [_serializar(t) for t in transacoes]


async def criar(session: AsyncSession, usuario_id: int, body: dict) -> dict:
    faltando = [
        campo
        for campo in ("data", "valor", "tipo", "categoria")
        if body.get(campo) in (None, "")
    ]
    if faltando:
        raise ValidacaoError(f"Campos obrigatorios ausentes: {', '.join(faltando)}")

    try:
        tipo = TipoEnum(body["tipo"])
        categoria = CategoriaEnum(body["categoria"])
        valor = Decimal(str(body["valor"]))
        data = date.fromisoformat(body["data"])
        status = StatusEnum(body["status"]) if body.get("status") is not None else None
        forma_pagamento = (
            FormaPagamentoEnum(body["forma_pagamento"])
            if body.get("forma_pagamento") is not None
            else FormaPagamentoEnum.PIX
        )
    except (ValueError, TypeError, InvalidOperation):
        raise ValidacaoError(
            "Campos invalidos: verifique data, valor, tipo, "
            "categoria, status e forma_pagamento"
        )

    if status is None:
        if forma_pagamento == FormaPagamentoEnum.PIX:
            status = StatusEnum.PAGO
        elif tipo == TipoEnum.RECEITA and data <= date.today():
            status = StatusEnum.PAGO
        else:
            status = StatusEnum.PENDENTE

    transacao = TransacaoCreate(
        usuario_id=usuario_id,
        tipo=tipo,
        valor=valor,
        descricao=body.get("descricao"),
        categoria=categoria,
        data=data,
        parcela_numero=1,
        parcela_total=1,
        grupo_parcela_id=uuid4(),
        embedding=None,
        status=status,
        forma_pagamento=forma_pagamento,
        responsavel=body.get("responsavel") or "Jhonatas",
        detalhes=body.get("detalhes"),
    )

    novo = await _repo(session).criar(transacao)
    return {"id": novo.id, "ok": True}


async def obter(session: AsyncSession, id: int) -> dict:
    transacao = await _repo(session).buscar_por_id(id, usuario_id=None)
    if transacao is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)
    return _serializar(transacao)


async def atualizar(session: AsyncSession, id: int, body: dict) -> dict:
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
        if "tipo" in body:
            campos["tipo"] = TipoEnum(body["tipo"])
        if "status" in body:
            campos["status"] = StatusEnum(body["status"])
        if "forma_pagamento" in body:
            campos["forma_pagamento"] = FormaPagamentoEnum(body["forma_pagamento"])
        if "responsavel" in body:
            campos["responsavel"] = body["responsavel"]
        if "detalhes" in body:
            campos["detalhes"] = body["detalhes"]
    except (ValueError, TypeError, InvalidOperation):
        raise ValidacaoError(
            "Campos invalidos: verifique data, valor, categoria, "
            "status e forma_pagamento"
        )

    repo = _repo(session)
    if await repo.buscar_por_id(id, usuario_id=None) is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)
    await repo.atualizar(id, TransacaoUpdate(**campos), usuario_id=None)
    return {"ok": True}


async def excluir(session: AsyncSession, id: int) -> dict:
    repo = _repo(session)
    if await repo.buscar_por_id(id, usuario_id=None) is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)
    await repo.excluir(id, usuario_id=None)
    return {"ok": True}
