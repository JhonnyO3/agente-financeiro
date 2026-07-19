import math
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.enums import CategoriaEnum, FormaPagamentoEnum, StatusEnum, TipoEnum
from backend.models.transacao import Transacao
from backend.repositories.cartao_repository import CartaoRepository
from backend.repositories.dtos import TransacaoCreate, TransacaoUpdate
from backend.repositories.transacao_repository import TransacaoRepository
from backend.services._parcelas import adicionar_meses, valores_das_parcelas
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
        "recorrente": t.recorrente,
        "responsavel": t.responsavel,
        "detalhes": t.detalhes or "",
        "cartao_id": getattr(t, "cartao_id", None),
    }


async def _validar_cartao(
    session: AsyncSession, usuario_id: int, cartao_id_raw
) -> int | None:
    if cartao_id_raw in (None, ""):
        return None
    try:
        cartao_id = int(cartao_id_raw)
    except (ValueError, TypeError):
        raise ValidacaoError("Cartao invalido")
    cartao = await CartaoRepository(session).buscar_por_id(cartao_id, usuario_id)
    if cartao is None:
        raise ValidacaoError("Cartao invalido")
    return cartao_id


async def listar(
    session: AsyncSession,
    usuario_id: int,
    periodo: str,
    tipo: str | None,
    categoria: str | None,
    status: str | None,
    pagina: int,
    forma_pagamento: str | None = None,
    ordenar: str | None = None,
    direcao: str = "desc",
    data_inicio: date | None = None,
    data_fim: date | None = None,
    cartao_id: int | None = None,
    sem_cartao: bool = False,
) -> dict:
    if data_inicio or data_fim:
        inicio = data_inicio or date(2000, 1, 1)
        fim    = data_fim    or date(2099, 12, 31)
    else:
        inicio, fim = resolver_periodo(periodo)
    repo = TransacaoRepository(session)
    transacoes = await repo.listar_por_periodo(inicio, fim, usuario_id=usuario_id)

    filtrada = [
        t
        for t in transacoes
        if (tipo is None or _como_str(t.tipo) == tipo)
        and (categoria is None or _como_str(t.categoria) == categoria)
        and (status is None or _como_str(t.status) == status)
        and (forma_pagamento is None or _como_str(t.forma_pagamento) == forma_pagamento)
        and (cartao_id is None or getattr(t, "cartao_id", None) == cartao_id)
        and (not sem_cartao or getattr(t, "cartao_id", None) is None)
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


async def criar(session: AsyncSession, usuario_id: int, body: dict) -> dict:
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

    parcelas_raw = body.get("parcelas")
    if parcelas_raw in (None, ""):
        parcelas = 1
    else:
        try:
            parcelas = int(parcelas_raw)
        except (ValueError, TypeError):
            raise ValidacaoError("Quantidade de parcelas invalida")
    if parcelas < 1:
        raise ValidacaoError("Quantidade de parcelas invalida")

    if status is None:
        if forma_pagamento == FormaPagamentoEnum.PIX:
            status = StatusEnum.PAGO
        elif tipo == TipoEnum.RECEITA and data <= date.today():
            status = StatusEnum.PAGO
        else:
            status = StatusEnum.PENDENTE

    responsavel = body.get("responsavel") or "Jhonatas"
    descricao = body.get("descricao")
    detalhes = body.get("detalhes")
    recorrente = bool(body.get("recorrente", False))
    cartao_id = await _validar_cartao(session, usuario_id, body.get("cartao_id"))

    repo = TransacaoRepository(session)

    if forma_pagamento == FormaPagamentoEnum.CARTAO_CREDITO and parcelas > 1:
        grupo_id = uuid4()
        valores = valores_das_parcelas(valor, parcelas)
        transacoes = [
            TransacaoCreate(
                usuario_id=usuario_id,
                tipo=tipo,
                valor=valores[i],
                descricao=descricao,
                categoria=categoria,
                data=adicionar_meses(data, i + 1),
                parcela_numero=i + 1,
                parcela_total=parcelas,
                grupo_parcela_id=grupo_id,
                embedding=None,
                status=StatusEnum.PENDENTE,
                forma_pagamento=forma_pagamento,
                recorrente=recorrente,
                responsavel=responsavel,
                detalhes=detalhes,
                cartao_id=cartao_id,
            )
            for i in range(parcelas)
        ]
        await repo.criar_lote(transacoes)
        return {"ok": True, "parcelas": parcelas, "grupo_parcela_id": str(grupo_id)}

    transacao = TransacaoCreate(
        usuario_id=usuario_id,
        tipo=tipo,
        valor=valor,
        descricao=descricao,
        categoria=categoria,
        data=data,
        parcela_numero=1,
        parcela_total=1,
        grupo_parcela_id=uuid4(),
        embedding=None,
        status=status,
        forma_pagamento=forma_pagamento,
        recorrente=recorrente,
        responsavel=responsavel,
        detalhes=detalhes,
        cartao_id=cartao_id,
    )
    novo = await repo.criar(transacao)
    return {"id": novo.id, "ok": True}


async def atualizar(session: AsyncSession, usuario_id: int, id: int, body: dict) -> dict:
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
        if "recorrente" in body:
            campos["recorrente"] = bool(body["recorrente"])
        if "responsavel" in body:
            campos["responsavel"] = body["responsavel"]
        if "detalhes" in body:
            campos["detalhes"] = body["detalhes"]
    except (ValueError, TypeError, InvalidOperation):
        raise ValidacaoError(
            "Campos invalidos: verifique data, valor, categoria, "
            "status e forma_pagamento"
        )

    if "cartao_id" in body and body["cartao_id"] not in (None, ""):
        campos["cartao_id"] = await _validar_cartao(
            session, usuario_id, body["cartao_id"]
        )

    repo = TransacaoRepository(session)
    if await repo.buscar_por_id(id, usuario_id=usuario_id) is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)
    await repo.atualizar(id, TransacaoUpdate(**campos), usuario_id=usuario_id)
    return {"ok": True}


async def excluir(session: AsyncSession, usuario_id: int, id: int) -> dict:
    repo = TransacaoRepository(session)
    if await repo.buscar_por_id(id, usuario_id=usuario_id) is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)
    await repo.excluir(id, usuario_id=usuario_id)
    return {"ok": True}


async def atualizar_status_em_lote(
    session: AsyncSession,
    usuario_id: int,
    ids: list[int] | None,
    status: str | None,
) -> dict:
    if not ids:
        raise ValidacaoError("Informe ao menos um id")
    try:
        status_enum = StatusEnum(status)
    except (ValueError, TypeError):
        raise ValidacaoError("Status invalido")

    stmt = (
        update(Transacao)
        .where(Transacao.id.in_(ids))
        .where(Transacao.usuario_id == usuario_id)
        .values(status=status_enum)
    )
    resultado = await session.execute(stmt)
    return {"atualizados": resultado.rowcount}


async def vincular_cartao_em_lote(
    session: AsyncSession,
    usuario_id: int,
    ids: list[int] | None,
    cartao_id: int | None,
) -> dict:
    if not ids:
        raise ValidacaoError("Informe ao menos um id")

    if cartao_id is not None:
        cartao = await CartaoRepository(session).buscar_por_id(cartao_id, usuario_id)
        if cartao is None:
            raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)

    repo = TransacaoRepository(session)
    transacoes = await repo.listar_por_ids(ids, usuario_id=usuario_id)

    grupos = sorted({t.grupo_parcela_id for t in transacoes if t.parcela_total > 1})
    ids_diretos = [t.id for t in transacoes if t.parcela_total <= 1]

    atualizados = await repo.vincular_cartao(
        ids_diretos, grupos, cartao_id, usuario_id
    )
    return {"atualizados": atualizados}
