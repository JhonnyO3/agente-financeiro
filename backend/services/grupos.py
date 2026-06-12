from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.enums import (
    CategoriaEnum,
    FormaPagamentoEnum,
    StatusEnum,
    TipoEnum,
)
from backend.repositories.dtos import TransacaoCreate
from backend.repositories.transacao_repository import TransacaoRepository
from backend.services.datas_parcela import datas_do_grupo


class IdInvalidoError(Exception):
    pass


class ValidacaoError(Exception):
    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class GrupoNaoEncontradoError(Exception):
    pass


def _parse_valor(raw) -> Decimal:
    try:
        v = Decimal(str(raw))
    except (InvalidOperation, TypeError):
        raise ValidacaoError("valor_parcela invalido")
    return v


def _parse_data(raw) -> date:
    try:
        return date.fromisoformat(str(raw))
    except (ValueError, TypeError):
        raise ValidacaoError("proxima_data invalida")


async def editar_grupo(
    session: AsyncSession, usuario_id: int, grupo_parcela_id: str, body: dict
) -> dict:
    # Validar UUID
    try:
        gid = UUID(grupo_parcela_id)
    except (ValueError, AttributeError):
        raise IdInvalidoError("ID inválido")

    # Campos obrigatórios
    obrigatorios = [
        "descricao",
        "valor_parcela",
        "proxima_data",
        "parcela_atual",
        "parcela_total",
    ]
    faltando = [c for c in obrigatorios if body.get(c) in (None, "")]
    if faltando:
        raise ValidacaoError(f"Campos obrigatorios ausentes: {', '.join(faltando)}")

    valor = _parse_valor(body["valor_parcela"])
    if valor <= Decimal("0"):
        raise ValidacaoError("valor_parcela deve ser maior que zero")

    try:
        parcela_atual = int(body["parcela_atual"])
        parcela_total = int(body["parcela_total"])
    except (ValueError, TypeError):
        raise ValidacaoError("parcela_atual e parcela_total devem ser inteiros")

    if parcela_total < 1:
        raise ValidacaoError("parcela_total deve ser >= 1")
    if parcela_total < parcela_atual:
        raise ValidacaoError("parcela_total nao pode ser menor que parcela_atual")

    proxima_data = _parse_data(body["proxima_data"])
    descricao = body["descricao"]

    # Carregar grupo
    repo = TransacaoRepository(session)
    linhas = await repo.buscar_por_grupo_com_embedding(gid, usuario_id=usuario_id)
    if not linhas:
        raise GrupoNaoEncontradoError("Grupo nao encontrado")

    total_original = linhas[0].parcela_total

    # Datas para toda a cadeia (baseado no parcela_total novo)
    todas_datas = datas_do_grupo(proxima_data, parcela_atual, parcela_total)

    # Referência para cópia de metadados ao aumentar
    ref = linhas[0]

    # Mutar linhas existentes; as acima do novo total serão excluídas adiante
    for linha in linhas:
        if linha.parcela_numero > parcela_total:
            continue
        linha.descricao = descricao
        linha.parcela_total = parcela_total
        # Status baseado em parcela_atual
        if linha.parcela_numero < parcela_atual:
            linha.status = StatusEnum.PAGO
        else:
            linha.status = StatusEnum.PENDENTE
            linha.valor = valor
            # Data da cadeia: índice = parcela_numero - 1
            linha.data = todas_datas[linha.parcela_numero - 1]

    if parcela_total > total_original:
        # Aumentar: criar linhas novas
        novos_dtos = []
        for num in range(total_original + 1, parcela_total + 1):
            dto = TransacaoCreate(
                usuario_id=usuario_id,
                tipo=ref.tipo,
                valor=valor,
                descricao=descricao,
                categoria=ref.categoria,
                data=todas_datas[num - 1],
                parcela_numero=num,
                parcela_total=parcela_total,
                grupo_parcela_id=gid,
                embedding=ref.embedding,
                status=StatusEnum.PENDENTE,
                forma_pagamento=ref.forma_pagamento,
                recorrente=ref.recorrente,
                responsavel=ref.responsavel,
            )
            novos_dtos.append(dto)
        await repo.criar_lote(novos_dtos)

    elif parcela_total < total_original:
        # Diminuir: excluir linhas finais
        numeros_excluir = list(range(parcela_total + 1, total_original + 1))
        await repo.excluir_por_grupo_e_numeros(
            gid, numeros_excluir, usuario_id=usuario_id
        )

    return {
        "ok": True,
        "grupo_parcela_id": str(gid),
        "parcela_total": parcela_total,
    }


async def criar_grupo(session: AsyncSession, usuario_id: int, body: dict) -> dict:
    # Campos obrigatórios
    obrigatorios = ["descricao", "valor_parcela", "parcela_total", "proxima_data"]
    faltando = [c for c in obrigatorios if body.get(c) in (None, "")]
    if faltando:
        raise ValidacaoError(f"Campos obrigatorios ausentes: {', '.join(faltando)}")

    valor = _parse_valor(body["valor_parcela"])
    if valor <= Decimal("0"):
        raise ValidacaoError("valor_parcela deve ser maior que zero")

    try:
        parcela_total = int(body["parcela_total"])
    except (ValueError, TypeError):
        raise ValidacaoError("parcela_total deve ser inteiro")

    if parcela_total < 2:
        raise ValidacaoError("parcela_total deve ser >= 2")

    raw_parcela_atual = body.get("parcela_atual")
    parcela_atual = int(raw_parcela_atual) if raw_parcela_atual is not None else 1

    if parcela_atual < 1:
        raise ValidacaoError("parcela_atual deve ser >= 1")
    if parcela_atual > parcela_total:
        raise ValidacaoError("parcela_atual nao pode ser maior que parcela_total")

    proxima_data = _parse_data(body["proxima_data"])
    descricao = body["descricao"]

    # Defaults opcionais
    try:
        categoria = (
            CategoriaEnum(body["categoria"])
            if body.get("categoria")
            else CategoriaEnum.COMPRAS
        )
    except ValueError:
        raise ValidacaoError("categoria invalida")

    try:
        forma_pagamento = (
            FormaPagamentoEnum(body["forma_pagamento"])
            if body.get("forma_pagamento")
            else FormaPagamentoEnum.CARTAO_CREDITO
        )
    except ValueError:
        raise ValidacaoError("forma_pagamento invalida")

    responsavel = body.get("responsavel") or "Jhonatas"

    gid = uuid4()
    todas_datas = datas_do_grupo(proxima_data, parcela_atual, parcela_total)

    dtos = []
    for num in range(1, parcela_total + 1):
        status = StatusEnum.PAGO if num < parcela_atual else StatusEnum.PENDENTE
        dto = TransacaoCreate(
            usuario_id=usuario_id,
            tipo=TipoEnum.GASTO,
            valor=valor,
            descricao=descricao,
            categoria=categoria,
            data=todas_datas[num - 1],
            parcela_numero=num,
            parcela_total=parcela_total,
            grupo_parcela_id=gid,
            embedding=None,  # type: ignore[arg-type]
            status=status,
            forma_pagamento=forma_pagamento,
            recorrente=False,
            responsavel=responsavel,
        )
        dtos.append(dto)

    repo = TransacaoRepository(session)
    await repo.criar_lote(dtos)

    return {
        "ok": True,
        "grupo_parcela_id": str(gid),
        "parcela_total": parcela_total,
    }
