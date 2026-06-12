from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.enums import (
    CategoriaEnum,
    FormaPagamentoEnum,
    StatusEnum,
    TipoEnum,
)
from backend.repositories.dtos import TransacaoCreate, TransacaoUpdate
from backend.repositories.transacao_repository import TransacaoRepository


class ValidacaoError(Exception):
    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoEncontradaError(Exception):
    pass


def _como_str(campo) -> str:
    return campo if isinstance(campo, str) else campo.value


async def listar(session: AsyncSession, usuario_id: int) -> dict:
    repo = TransacaoRepository(session)
    itens = await repo.listar_recorrentes(usuario_id)
    itens_ordenados = sorted(itens, key=lambda t: t.data.day)
    total = sum(t.valor for t in itens_ordenados)
    return {
        "itens": [
            {
                "id": t.id,
                "descricao": t.descricao or "",
                "valor": str(t.valor.quantize(Decimal("0.01"))),
                "dia_vencimento": t.data.day,
                "data": t.data.isoformat(),
                "categoria": _como_str(t.categoria),
                "forma_pagamento": _como_str(t.forma_pagamento),
                "responsavel": t.responsavel,
                "status": _como_str(t.status),
            }
            for t in itens_ordenados
        ],
        "total_mensal": str(total.quantize(Decimal("0.01")))
        if itens_ordenados
        else "0.00",
    }


async def criar(session: AsyncSession, usuario_id: int, body: dict) -> dict:
    obrigatorios = ["descricao", "valor", "data"]
    faltando = [c for c in obrigatorios if body.get(c) in (None, "")]
    if faltando:
        raise ValidacaoError(f"Campos obrigatorios ausentes: {', '.join(faltando)}")

    try:
        valor = Decimal(str(body["valor"]))
    except (InvalidOperation, TypeError):
        raise ValidacaoError("valor invalido")

    if valor <= Decimal("0"):
        raise ValidacaoError("valor deve ser maior que zero")

    try:
        data = date.fromisoformat(str(body["data"]))
    except (ValueError, TypeError):
        raise ValidacaoError("data invalida")

    try:
        categoria = (
            CategoriaEnum(body["categoria"])
            if body.get("categoria")
            else CategoriaEnum.GASTOS_FIXOS
        )
    except ValueError:
        raise ValidacaoError("categoria invalida")

    try:
        forma_pagamento = (
            FormaPagamentoEnum(body["forma_pagamento"])
            if body.get("forma_pagamento")
            else FormaPagamentoEnum.PIX
        )
    except ValueError:
        raise ValidacaoError("forma_pagamento invalida")

    responsavel = body.get("responsavel") or "Jhonatas"
    status = (
        StatusEnum.PAGO
        if forma_pagamento == FormaPagamentoEnum.PIX
        else StatusEnum.PENDENTE
    )

    dto = TransacaoCreate(
        usuario_id=usuario_id,
        tipo=TipoEnum.GASTO,
        valor=valor,
        descricao=body.get("descricao"),
        categoria=categoria,
        data=data,
        parcela_numero=1,
        parcela_total=1,
        grupo_parcela_id=uuid4(),
        embedding=None,  # type: ignore[arg-type]
        status=status,
        forma_pagamento=forma_pagamento,
        recorrente=True,
        responsavel=responsavel,
    )

    repo = TransacaoRepository(session)
    novo = await repo.criar(dto)
    return {"id": novo.id, "ok": True}


async def atualizar(
    session: AsyncSession, usuario_id: int, id: int, body: dict
) -> dict:
    repo = TransacaoRepository(session)
    transacao = await repo.buscar_por_id(id, usuario_id=usuario_id)
    if transacao is None or not transacao.recorrente:
        raise NaoEncontradaError("Gasto fixo nao encontrado")

    campos: dict = {}
    try:
        if "descricao" in body:
            campos["descricao"] = body["descricao"]
        if "valor" in body:
            v = Decimal(str(body["valor"]))
            if v <= Decimal("0"):
                raise ValidacaoError("valor deve ser maior que zero")
            campos["valor"] = v
        if "data" in body:
            campos["data"] = date.fromisoformat(str(body["data"]))
        if "categoria" in body:
            campos["categoria"] = CategoriaEnum(body["categoria"])
        if "forma_pagamento" in body:
            campos["forma_pagamento"] = FormaPagamentoEnum(body["forma_pagamento"])
        if "responsavel" in body:
            campos["responsavel"] = body["responsavel"]
    except ValidacaoError:
        raise
    except (ValueError, TypeError, InvalidOperation):
        raise ValidacaoError(
            "Campos invalidos: verifique data, valor, categoria e forma_pagamento"
        )

    await repo.atualizar(id, TransacaoUpdate(**campos), usuario_id=usuario_id)
    return {"ok": True}


async def excluir(session: AsyncSession, usuario_id: int, id: int) -> dict:
    repo = TransacaoRepository(session)
    transacao = await repo.buscar_por_id(id, usuario_id=usuario_id)
    if transacao is None or not transacao.recorrente:
        raise NaoEncontradaError("Gasto fixo nao encontrado")
    await repo.excluir(id, usuario_id=usuario_id)
    return {"ok": True}
