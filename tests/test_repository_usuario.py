from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from backend.models.enums import CategoriaEnum, RoleEnum, TipoEnum
from backend.repositories.dtos import TransacaoCreate, TransacaoUpdate, UsuarioCreate
from backend.repositories.transacao_repository import TransacaoRepository
from backend.repositories.usuario_repository import UsuarioRepository


def make_transacao_dto(**kwargs) -> TransacaoCreate:
    defaults = dict(
        usuario_id=1,
        tipo=TipoEnum.GASTO,
        valor=Decimal("50.00"),
        descricao="mercado",
        categoria=CategoriaEnum.ALIMENTACAO,
        data=date(2026, 6, 9),
        parcela_numero=1,
        parcela_total=1,
        grupo_parcela_id=uuid4(),
        embedding=[0.1] * 1536,
    )
    defaults.update(kwargs)
    return TransacaoCreate(**defaults)


# ---------------------------------------------------------------------------
# TransacaoCreate / TransacaoUpdate DTOs
# ---------------------------------------------------------------------------


def test_transacao_create_exige_usuario_id():
    with pytest.raises(TypeError):
        TransacaoCreate(
            tipo=TipoEnum.GASTO,
            valor=Decimal("50.00"),
            descricao="mercado",
            categoria=CategoriaEnum.ALIMENTACAO,
            data=date(2026, 6, 9),
            parcela_numero=1,
            parcela_total=1,
            grupo_parcela_id=uuid4(),
            embedding=[0.1] * 1536,
        )


def test_transacao_create_persiste_usuario_id():
    dto = make_transacao_dto(usuario_id=7)
    assert dto.usuario_id == 7


def test_transacao_update_nao_possui_usuario_id():
    dto = TransacaoUpdate()
    assert not hasattr(dto, "usuario_id")


def test_transacao_update_rejeita_usuario_id_no_construtor():
    with pytest.raises(TypeError):
        TransacaoUpdate(usuario_id=1)


# ---------------------------------------------------------------------------
# TransacaoRepository.criar grava usuario_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_criar_grava_usuario_id():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TransacaoRepository(session)
    await repo.criar(make_transacao_dto(usuario_id=42))

    obj = session.add.call_args[0][0]
    assert obj.usuario_id == 42


@pytest.mark.asyncio
async def test_criar_lote_grava_usuario_id():
    session = MagicMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TransacaoRepository(session)
    grupo_id = uuid4()
    dtos = [
        make_transacao_dto(usuario_id=9, grupo_parcela_id=grupo_id, parcela_numero=i + 1)
        for i in range(3)
    ]
    await repo.criar_lote(dtos)

    objetos = session.add_all.call_args[0][0]
    assert all(obj.usuario_id == 9 for obj in objetos)


# ---------------------------------------------------------------------------
# TransacaoRepository — filtro por usuario_id
# ---------------------------------------------------------------------------


def _compilar(stmt) -> str:
    return str(stmt.compile(compile_kwargs={"literal_binds": False}))


def _where(stmt) -> str:
    clause = stmt.whereclause
    return str(clause.compile(compile_kwargs={"literal_binds": False})) if clause is not None else ""


@pytest.mark.asyncio
async def test_listar_por_periodo_filtra_por_usuario_id():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    await repo.listar_por_periodo(date(2026, 6, 1), date(2026, 6, 30), usuario_id=1)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" in _where(stmt)


@pytest.mark.asyncio
async def test_listar_por_periodo_sem_usuario_id_nao_filtra():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    await repo.listar_por_periodo(date(2026, 6, 1), date(2026, 6, 30), usuario_id=None)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" not in _where(stmt)


@pytest.mark.asyncio
async def test_buscar_por_id_filtra_por_usuario_id():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    await repo.buscar_por_id(10, usuario_id=2)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" in _where(stmt)


@pytest.mark.asyncio
async def test_buscar_por_id_sem_usuario_id_nao_filtra():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    await repo.buscar_por_id(10)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" not in _where(stmt)


@pytest.mark.asyncio
async def test_buscar_por_grupo_filtra_por_usuario_id():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    await repo.buscar_por_grupo(uuid4(), usuario_id=1)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" in _where(stmt)


@pytest.mark.asyncio
async def test_excluir_filtra_por_usuario_id():
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.flush = AsyncMock()

    repo = TransacaoRepository(session)
    await repo.excluir(10, usuario_id=2)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" in _where(stmt)


@pytest.mark.asyncio
async def test_excluir_grupo_filtra_por_usuario_id():
    mock_result = MagicMock()
    mock_result.rowcount = 0

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()

    repo = TransacaoRepository(session)
    await repo.excluir_grupo(uuid4(), usuario_id=2)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" in _where(stmt)


@pytest.mark.asyncio
async def test_excluir_grupo_sem_usuario_id_nao_filtra():
    mock_result = MagicMock()
    mock_result.rowcount = 3

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()

    repo = TransacaoRepository(session)
    await repo.excluir_grupo(uuid4(), usuario_id=None)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" not in _where(stmt)


@pytest.mark.asyncio
async def test_agregar_por_categoria_filtra_por_usuario_id():
    mock_result = MagicMock()
    mock_result.all.return_value = []

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    await repo.agregar_por_categoria(date(2026, 6, 1), date(2026, 6, 30), usuario_id=1)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" in _where(stmt)


@pytest.mark.asyncio
async def test_atualizar_filtra_por_usuario_id_no_buscar():
    transacao = MagicMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = transacao

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = TransacaoRepository(session)
    await repo.atualizar(10, TransacaoUpdate(descricao="nova"), usuario_id=1)

    stmt = session.execute.call_args[0][0]
    assert "usuario_id" in _where(stmt)


# ---------------------------------------------------------------------------
# UsuarioRepository
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_usuario_criar_chama_add_e_flush():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = UsuarioRepository(session)
    dto = UsuarioCreate(
        nome="Bob",
        username="bob",
        email="bob@example.com",
        senha_hash="hash",
        role=RoleEnum.USER,
    )
    await repo.criar(dto)

    obj = session.add.call_args[0][0]
    assert obj.email == "bob@example.com"
    assert obj.senha_hash == "hash"
    assert obj.role == RoleEnum.USER
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_usuario_criar_aceita_kwargs():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = UsuarioRepository(session)
    await repo.criar(
        nome="Bob",
        username="bob",
        email="bob@example.com",
        senha_hash="hash",
    )

    obj = session.add.call_args[0][0]
    assert obj.email == "bob@example.com"


@pytest.mark.asyncio
async def test_usuario_buscar_por_email_retorna_usuario():
    usuario = MagicMock()
    usuario.email = "carol@example.com"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = usuario

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = UsuarioRepository(session)
    resultado = await repo.buscar_por_email("carol@example.com")

    assert resultado.email == "carol@example.com"
    stmt = session.execute.call_args[0][0]
    assert "email" in _compilar(stmt)


@pytest.mark.asyncio
async def test_usuario_buscar_por_email_inexistente_retorna_none():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = UsuarioRepository(session)
    resultado = await repo.buscar_por_email("desconhecido@example.com")

    assert resultado is None


@pytest.mark.asyncio
async def test_usuario_criar_email_duplicado_propaga_erro():
    from sqlalchemy.exc import IntegrityError

    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock(side_effect=IntegrityError("dup", {}, Exception()))

    repo = UsuarioRepository(session)
    dto = UsuarioCreate(
        nome="Dup",
        username="dup",
        email="duplicado@example.com",
        senha_hash="hash",
    )
    with pytest.raises(IntegrityError):
        await repo.criar(dto)


@pytest.mark.asyncio
async def test_usuario_listar_retorna_todos():
    usuarios = [MagicMock() for _ in range(4)]

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = usuarios

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = UsuarioRepository(session)
    resultado = await repo.listar()

    assert len(resultado) == 4


@pytest.mark.asyncio
async def test_usuario_buscar_por_id_retorna_none_quando_ausente():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = UsuarioRepository(session)
    resultado = await repo.buscar_por_id(999)

    assert resultado is None


@pytest.mark.asyncio
async def test_usuario_atualizar_persiste_mudancas():
    usuario = MagicMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = usuario

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    repo = UsuarioRepository(session)
    await repo.atualizar(5, nome="Novo")

    assert usuario.nome == "Novo"
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_usuario_excluir_executa_delete():
    session = MagicMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.flush = AsyncMock()

    repo = UsuarioRepository(session)
    await repo.excluir(7)

    stmt = session.execute.call_args[0][0]
    assert "usuarios" in _compilar(stmt)
    session.flush.assert_awaited_once()
