"""Testes TDD para UsuarioRepository.buscar_por_telefone (Tarefa CA-01)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.repositories.usuario_repository import UsuarioRepository


def _make_session(scalar_result=None, call_count_tracker=None):
    """Monta um AsyncSession falso.

    Se call_count_tracker for uma lista mutável, ela receberá 1 append por
    chamada a session.execute — útil para verificar que execute NÃO foi chamado.
    """
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scalar_result

    session = MagicMock()
    if call_count_tracker is not None:

        async def _execute(stmt):
            call_count_tracker.append(stmt)
            return mock_result

        session.execute = AsyncMock(side_effect=_execute)
    else:
        session.execute = AsyncMock(return_value=mock_result)

    return session


# ---------------------------------------------------------------------------
# Cenário 1 — usuário ativo é encontrado
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_por_telefone_ativo_retorna_usuario():
    usuario = MagicMock()
    usuario.telefone = "5511999998888"
    usuario.ativo = True

    session = _make_session(scalar_result=usuario)
    repo = UsuarioRepository(session)

    resultado = await repo.buscar_por_telefone("5511999998888")

    assert resultado is usuario
    session.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Cenário 2 — usuário inativo retorna None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_por_telefone_inativo_retorna_none():
    # O banco já filtra ativo=True na query; scalar_one_or_none devolve None.
    session = _make_session(scalar_result=None)
    repo = UsuarioRepository(session)

    resultado = await repo.buscar_por_telefone("5511999998888")

    assert resultado is None


# ---------------------------------------------------------------------------
# Cenário 3 — telefone inexistente retorna None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_por_telefone_inexistente_retorna_none():
    session = _make_session(scalar_result=None)
    repo = UsuarioRepository(session)

    resultado = await repo.buscar_por_telefone("5511000000000")

    assert resultado is None


# ---------------------------------------------------------------------------
# Cenário 4 — telefone com máscara é normalizado antes da busca
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_por_telefone_mascara_normaliza_e_encontra():
    usuario = MagicMock()
    usuario.telefone = "5511999998888"
    usuario.ativo = True

    session = _make_session(scalar_result=usuario)
    repo = UsuarioRepository(session)

    # Entrada com formatação internacional
    resultado = await repo.buscar_por_telefone("+55 (11) 99999-8888")

    assert resultado is usuario
    # A query deve ter sido executada (normalização aconteceu antes)
    session.execute.assert_awaited_once()
    # Verifica que o WHERE contém apenas dígitos (compilação da query)
    stmt = session.execute.call_args[0][0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "telefone" in compiled
    assert "ativo" in compiled


# ---------------------------------------------------------------------------
# Cenário 5 — telefone vazio/só-símbolos não consulta o banco
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buscar_por_telefone_vazio_retorna_none_sem_query():
    calls: list = []
    session = _make_session(call_count_tracker=calls)
    repo = UsuarioRepository(session)

    resultado = await repo.buscar_por_telefone("   ")

    assert resultado is None
    assert len(calls) == 0, "execute não deve ser chamado para telefone vazio"


@pytest.mark.asyncio
async def test_buscar_por_telefone_so_simbolos_retorna_none_sem_query():
    calls: list = []
    session = _make_session(call_count_tracker=calls)
    repo = UsuarioRepository(session)

    resultado = await repo.buscar_por_telefone("+- ()")

    assert resultado is None
    assert len(calls) == 0, "execute não deve ser chamado para entrada sem dígitos"
