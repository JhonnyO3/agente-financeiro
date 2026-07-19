import datetime
from datetime import date
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from backend.dtos.recorrencia import (
    RecorrenciaCreate,
    RecorrenciaResponse,
    RecorrenciaUpdate,
)
from backend.models.enums import FormaPagamentoEnum, StatusEnum
from backend.repositories.dtos import TransacaoCreate
from backend.repositories.recorrencia_repository import RecorrenciaRepository
from backend.repositories.transacao_repository import TransacaoRepository
from backend.services.janela import janela_meses, ultimo_dia

ERRO_NAO_ENCONTRADA = "Recorrencia nao encontrada"


class NaoEncontradaError(Exception):
    pass


def _repo(session: AsyncSession) -> RecorrenciaRepository:
    return RecorrenciaRepository(session)


async def listar(
    session: AsyncSession, usuario_id: int, ativo: bool | None = None
) -> list[dict]:
    recorrencias = await _repo(session).listar(usuario_id, ativo=ativo)
    return [RecorrenciaResponse.de_modelo(r).model_dump() for r in recorrencias]


async def criar(
    session: AsyncSession, usuario_id: int, dados: RecorrenciaCreate
) -> dict:
    nova = await _repo(session).criar(
        usuario_id=usuario_id,
        descricao=dados.descricao,
        tipo=dados.tipo,
        categoria=dados.categoria,
        valor=dados.valor,
        dia_vencimento=dados.dia_vencimento,
        forma_pagamento=dados.forma_pagamento,
        ativo=dados.ativo,
    )
    return RecorrenciaResponse.de_modelo(nova).model_dump()


async def atualizar(
    session: AsyncSession, usuario_id: int, id: int, dados: RecorrenciaUpdate
) -> dict:
    repo = _repo(session)
    if await repo.buscar_por_id(id, usuario_id=usuario_id) is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)

    campos = dados.model_dump(exclude_unset=True)
    if "ativo" in campos:
        campos["encerrado_em"] = (
            None if campos["ativo"] else datetime.datetime.now()
        )
    atualizada = await repo.atualizar(id, campos, usuario_id=usuario_id)
    return RecorrenciaResponse.de_modelo(atualizada).model_dump()


async def excluir(session: AsyncSession, usuario_id: int, id: int) -> dict:
    repo = _repo(session)
    if await repo.buscar_por_id(id, usuario_id=usuario_id) is None:
        raise NaoEncontradaError(ERRO_NAO_ENCONTRADA)
    await repo.excluir(id, usuario_id=usuario_id)
    return {"ok": True}


def _data_vencimento(competencia: date, dia_vencimento: int | None) -> date:
    if dia_vencimento is None:
        return competencia
    ultimo = ultimo_dia(competencia).day
    dia = max(1, min(dia_vencimento, ultimo))
    return competencia.replace(day=dia)


def _chave_recorrencia(descricao, categoria, tipo) -> tuple[str, str, str]:
    def _s(v) -> str:
        return getattr(v, "value", v)

    return ((descricao or "").strip().lower(), _s(categoria), _s(tipo))


async def garantir_janela(
    session: AsyncSession, usuario_id: int, hoje: date
) -> int:
    rec_repo = _repo(session)
    trans_repo = TransacaoRepository(session)

    competencias = janela_meses(hoje)[6:]
    recorrencias = await rec_repo.listar_ativas(usuario_id)

    gerados = 0
    for competencia in competencias:
        existentes = await trans_repo.listar_por_periodo(
            competencia, ultimo_dia(competencia), usuario_id=usuario_id
        )
        avulsos = {
            _chave_recorrencia(t.descricao, t.categoria, t.tipo)
            for t in existentes
            if getattr(t, "recorrencia_id", None) is None
        }
        for recorrencia in recorrencias:
            if await rec_repo.existe_lancamento(recorrencia.id, competencia):
                continue
            chave = _chave_recorrencia(
                recorrencia.descricao, recorrencia.categoria, recorrencia.tipo
            )
            if chave in avulsos:
                await rec_repo.registrar_lancamento(recorrencia.id, competencia, None)
                continue
            data = _data_vencimento(competencia, recorrencia.dia_vencimento)
            transacao = await trans_repo.criar(
                TransacaoCreate(
                    usuario_id=usuario_id,
                    tipo=recorrencia.tipo,
                    valor=recorrencia.valor,
                    descricao=recorrencia.descricao,
                    categoria=recorrencia.categoria,
                    data=data,
                    parcela_numero=1,
                    parcela_total=1,
                    grupo_parcela_id=uuid4(),
                    embedding=None,
                    status=StatusEnum.PENDENTE,
                    forma_pagamento=(
                        recorrencia.forma_pagamento or FormaPagamentoEnum.PIX
                    ),
                    recorrencia_id=recorrencia.id,
                )
            )
            await rec_repo.registrar_lancamento(
                recorrencia.id, competencia, transacao.id
            )
            gerados += 1
    return gerados
