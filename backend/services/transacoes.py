import math
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.enums import CategoriaEnum, FormaPagamentoEnum, StatusEnum, TipoEnum
from backend.repositories.dtos import TransacaoCreate, TransacaoUpdate
from backend.repositories.transacao_repository import TransacaoRepository
from backend.services.resumo import resolver_periodo

POR_PAGINA = 25

ERRO_NAO_ENCONTRADA = "Transacao nao encontrada"


class ValidacaoError(Exception):
    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoEncontradaError(Exception):
    pass


def _como_str(campo) -> str:
    return campo if isinstance(campo, str) else campo.value


_CHAVES_ORDENACAO = {
    "data": lambda t: (t.data, t.id),
    "descricao": lambda t: (t.descricao or "").lower(),
    "categoria": lambda t: _como_str(t.categoria),
    "valor": lambda t: t.valor,
    "parcela": lambda t: (t.parcela_total, t.parcela_numero),
    "forma_pagamento": lambda t: _como_str(t.forma_pagamento),
    "tipo": lambda t: _como_str(t.tipo),
    "status": lambda t: _como_str(t.status),
    "responsavel": lambda t: (t.responsavel or "").lower(),
}


def _serializar(t) -> dict:
    return {
        "id": t.id,
        "data": t.data.isoformat(),
        "descricao": t.descricao or "",
        "categoria": _como_str(t.categoria),
        "valor": str(t.valor.quantize(Decimal("0.01"))),
        "parcela_numero": t.parcela_numero,
        "parcela_total": t.parcela_total,
        "tipo": _como_str(t.tipo),
        "grupo_parcela_id": t.grupo_parcela_id,
        "status": _como_str(t.status),
        "forma_pagamento": _como_str(t.forma_pagamento),
        "responsavel": t.responsavel,
        "detalhes": t.detalhes or "",
    }


async def listar(
    session: AsyncSession,
    periodo: str,
    tipo: str | None,
    categoria: str | None,
    status: str | None,
    pagina: int,
    forma_pagamento: str | None = None,
    ordenar: str | None = None,
    direcao: str = "desc",
) -> dict:
    inicio, fim = resolver_periodo(periodo)
    repo = TransacaoRepository(session)
    transacoes = await repo.listar_por_periodo(inicio, fim)

    filtrada = [
        t
        for t in transacoes
        if (tipo is None or _como_str(t.tipo) == tipo)
        and (categoria is None or _como_str(t.categoria) == categoria)
        and (status is None or _como_str(t.status) == status)
        and (forma_pagamento is None or _como_str(t.forma_pagamento) == forma_pagamento)
    ]
    chave = _CHAVES_ORDENACAO.get(ordenar)
    if chave is not None:
        filtrada.sort(key=chave, reverse=direcao != "asc")
    else:
        filtrada.sort(key=lambda t: (t.data, t.id), reverse=True)

    total = len(filtrada)
    paginas = math.ceil(total / POR_PAGINA)
    itens = filtrada[(pagina - 1) * POR_PAGINA : pagina * POR_PAGINA]

    return {
        "itens": [_serializar(t) for t in itens],
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "por_pagina": POR_PAGINA,
    }


async def criar(session: AsyncSession, body: dict) -> dict:
    faltando = [
        campo
        for campo in ("data", "valor", "tipo", "categoria")
        if body.get(campo) in (None, "")
    ]
    if faltando:
        raise ValidacaoError(
            f"Campos obrigatorios ausentes: {', '.join(faltando)}"
        )

    try:
        tipo = TipoEnum(body["tipo"])
        categoria = CategoriaEnum(body["categoria"])
        valor = Decimal(str(body["valor"]))
        data = date.fromisoformat(body["data"])
        status = (
            StatusEnum(body["status"]) if body.get("status") is not None else None
        )
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

    repo = TransacaoRepository(session)
    novo = await repo.criar(transacao)
    return {"id": novo.id, "ok": True}


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

    repo = TransacaoRepository(session)
    if await repo.buscar_por_id(id) is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)
    await repo.atualizar(id, TransacaoUpdate(**campos))
    return {"ok": True}


async def excluir(session: AsyncSession, id: int) -> dict:
    repo = TransacaoRepository(session)
    if await repo.buscar_por_id(id) is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)
    await repo.excluir(id)
    return {"ok": True}
