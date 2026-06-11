from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.hashing import hash_senha
from backend.dtos.usuario import (
    UsuarioCreateRequest,
    UsuarioResponse,
    UsuarioUpdateRequest,
)
from backend.repositories.dtos import UsuarioCreate, UsuarioUpdate
from backend.repositories.usuario_repository import UsuarioRepository

ERRO_NAO_ENCONTRADO = "Usuario nao encontrado"
ERRO_EMAIL_DUPLICADO = "Email ja cadastrado"


class NaoEncontradoError(Exception):
    pass


class EmailDuplicadoError(Exception):
    pass


def _repo(session: AsyncSession) -> UsuarioRepository:
    return UsuarioRepository(session)


async def listar(session: AsyncSession) -> list[dict]:
    usuarios = await _repo(session).listar()
    return [UsuarioResponse.de_modelo(u).model_dump() for u in usuarios]


async def obter(session: AsyncSession, id: int) -> dict:
    usuario = await _repo(session).buscar_por_id(id)
    if usuario is None:
        raise NaoEncontradoError(ERRO_NAO_ENCONTRADO)
    return UsuarioResponse.de_modelo(usuario).model_dump()


async def criar(session: AsyncSession, dados: UsuarioCreateRequest) -> dict:
    repo = _repo(session)
    if await repo.buscar_por_email(dados.email) is not None:
        raise EmailDuplicadoError(ERRO_EMAIL_DUPLICADO)

    novo = await repo.criar(
        UsuarioCreate(
            nome=dados.nome,
            username=dados.username,
            email=dados.email,
            senha_hash=hash_senha(dados.senha),
            telefone=dados.telefone,
            role=dados.role,
        )
    )
    return UsuarioResponse.de_modelo(novo).model_dump()


async def atualizar(session: AsyncSession, id: int, dados: UsuarioUpdateRequest) -> dict:
    repo = _repo(session)
    atual = await repo.buscar_por_id(id)
    if atual is None:
        raise NaoEncontradoError(ERRO_NAO_ENCONTRADO)

    if dados.email is not None and dados.email != atual.email:
        existente = await repo.buscar_por_email(dados.email)
        if existente is not None and existente.id != id:
            raise EmailDuplicadoError(ERRO_EMAIL_DUPLICADO)

    update = UsuarioUpdate(
        nome=dados.nome,
        username=dados.username,
        email=dados.email,
        senha_hash=hash_senha(dados.senha) if dados.senha is not None else None,
        telefone=dados.telefone,
        role=dados.role,
        ativo=dados.ativo,
    )
    atualizado = await repo.atualizar(id, update)
    return UsuarioResponse.de_modelo(atualizado).model_dump()


async def excluir(session: AsyncSession, id: int) -> dict:
    repo = _repo(session)
    if await repo.buscar_por_id(id) is None:
        raise NaoEncontradoError(ERRO_NAO_ENCONTRADO)
    await repo.excluir(id)
    return {"ok": True}
