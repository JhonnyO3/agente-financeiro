from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dtos.cartao import CartaoCreate, CartaoUpdate
from backend.models.cartao import Cartao
from backend.repositories.cartao_repository import CartaoRepository
from backend.repositories.transacao_repository import TransacaoRepository
from backend.services.resumo import resolver_periodo

ERRO_NAO_ENCONTRADO = "Cartao nao encontrado"

_DOIS_DECIMAIS = Decimal("0.01")


class ValidacaoError(Exception):
    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoEncontradoError(Exception):
    pass


def _como_str(campo) -> str:
    return campo.value if hasattr(campo, "value") else campo


def _serializar(cartao) -> dict:
    return {
        "id": cartao.id,
        "apelido": cartao.apelido,
        "dia_fechamento": cartao.dia_fechamento,
        "dia_vencimento": cartao.dia_vencimento,
        "cor": cartao.cor,
        "ativo": cartao.ativo,
    }


async def listar(session: AsyncSession, usuario_id: int) -> list[dict]:
    repo = CartaoRepository(session)
    cartoes = await repo.listar(usuario_id)
    return [_serializar(c) for c in cartoes]


async def criar(session: AsyncSession, usuario_id: int, body: dict) -> dict:
    try:
        dados = CartaoCreate(**body)
    except (ValidationError, TypeError):
        raise ValidacaoError("Dados invalidos: verifique apelido e dias")

    repo = CartaoRepository(session)
    cartao = Cartao(
        usuario_id=usuario_id,
        apelido=dados.apelido,
        dia_fechamento=dados.dia_fechamento,
        dia_vencimento=dados.dia_vencimento,
        cor=dados.cor,
        ativo=dados.ativo,
    )
    criado = await repo.criar(cartao)
    return _serializar(criado)


async def atualizar(
    session: AsyncSession, usuario_id: int, id: int, body: dict
) -> dict:
    try:
        dados = CartaoUpdate(**body)
    except (ValidationError, TypeError):
        raise ValidacaoError("Dados invalidos: verifique apelido e dias")

    repo = CartaoRepository(session)
    cartao = await repo.buscar_por_id(id, usuario_id)
    if cartao is None:
        raise NaoEncontradoError(ERRO_NAO_ENCONTRADO)

    campos = dados.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(cartao, campo, valor)
    atualizado = await repo.atualizar(cartao)
    return _serializar(atualizado)


async def excluir(session: AsyncSession, usuario_id: int, id: int) -> dict:
    repo = CartaoRepository(session)
    cartao = await repo.buscar_por_id(id, usuario_id)
    if cartao is None:
        raise NaoEncontradoError(ERRO_NAO_ENCONTRADO)
    await repo.excluir(id, usuario_id)
    return {"ok": True}


async def resumo(
    session: AsyncSession, usuario_id: int, id: int, periodo: str
) -> dict:
    cartao_repo = CartaoRepository(session)
    cartao = await cartao_repo.buscar_por_id(id, usuario_id)
    if cartao is None:
        raise NaoEncontradoError(ERRO_NAO_ENCONTRADO)

    inicio, fim = resolver_periodo(periodo)
    transacao_repo = TransacaoRepository(session)
    transacoes = await transacao_repo.listar_por_cartao(id, usuario_id)

    total_periodo = sum(
        (t.valor for t in transacoes if inicio <= t.data <= fim),
        Decimal("0"),
    )
    parcelas_abertas = [
        t
        for t in transacoes
        if t.parcela_total > 1 and _como_str(t.status) == "PENDENTE"
    ]
    soma_restante = sum((t.valor for t in parcelas_abertas), Decimal("0"))

    return {
        "cartao_id": id,
        "periodo": periodo,
        "total_periodo": str(total_periodo.quantize(_DOIS_DECIMAIS)),
        "parcelas_abertas": len(parcelas_abertas),
        "soma_restante": str(soma_restante.quantize(_DOIS_DECIMAIS)),
    }
