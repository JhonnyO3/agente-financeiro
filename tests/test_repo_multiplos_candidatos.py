import inspect
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_API_KEY", "test")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("AUTHORIZED_NUMBERS", "5511999999999")
os.environ.setdefault("ADMIN_EMAILS", "admin@exemplo.com")

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from backend.models.enums import CategoriaEnum, TipoEnum
from backend.repositories.transacao_repository import TransacaoRepository


def _make_transacao(usuario_id: int = 1) -> MagicMock:
    t = MagicMock()
    t.usuario_id = usuario_id
    t.id = 1
    return t


def _mock_session_with_rows(rows: list[tuple]) -> MagicMock:
    mock_result = MagicMock()
    mock_result.all.return_value = rows
    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    return session


# ---------------------------------------------------------------------------
# buscar_semantico_multiplos_com_distancia — método principal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiplos_retorna_lista_ordenada_por_distancia():
    t1, t2, t3 = _make_transacao(), _make_transacao(), _make_transacao()
    rows = [(t1, 0.5), (t2, 0.8), (t3, 1.2)]
    session = _mock_session_with_rows(rows)

    repo = TransacaoRepository(session)
    resultado = await repo.buscar_semantico_multiplos_com_distancia(
        [0.1] * 1536, limite=5, usuario_id=1
    )

    assert len(resultado) == 3
    distancias = [d for _, d in resultado]
    assert distancias == sorted(distancias), "distâncias devem estar em ordem crescente"


@pytest.mark.asyncio
async def test_multiplos_respeita_limite():
    rows = [(i, _make_transacao(), 0.1 * i) for i in range(5)]
    # rows como (Transacao, float) — limite é aplicado na query (mock devolve 2)
    rows_limitados = [(_make_transacao(), 0.1), (_make_transacao(), 0.2)]
    session = _mock_session_with_rows(rows_limitados)

    repo = TransacaoRepository(session)
    resultado = await repo.buscar_semantico_multiplos_com_distancia(
        [0.1] * 1536, limite=2, usuario_id=1
    )

    assert len(resultado) <= 2


@pytest.mark.asyncio
async def test_multiplos_filtra_usuario_id_na_query():
    """Verifica que a query executada inclui filtro de usuario_id."""
    session = _mock_session_with_rows([])

    repo = TransacaoRepository(session)
    await repo.buscar_semantico_multiplos_com_distancia(
        [0.1] * 1536, limite=5, usuario_id=42
    )

    session.execute.assert_awaited_once()
    stmt = session.execute.call_args[0][0]
    # A cláusula WHERE deve mencionar usuario_id=42
    stmt_str = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "42" in stmt_str, "filtro usuario_id=42 deve estar na query compilada"


@pytest.mark.asyncio
async def test_multiplos_usuario_id_none_nao_filtra():
    """Com usuario_id=None a query não deve incluir filtro de usuario_id."""
    session = _mock_session_with_rows([])

    repo = TransacaoRepository(session)
    await repo.buscar_semantico_multiplos_com_distancia(
        [0.1] * 1536, limite=5, usuario_id=None
    )

    session.execute.assert_awaited_once()
    stmt = session.execute.call_args[0][0]
    stmt_str = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "transacoes.usuario_id =" not in stmt_str, (
        "sem usuario_id não deve haver filtro WHERE na query"
    )


@pytest.mark.asyncio
async def test_multiplos_lista_vazia_quando_sem_resultados():
    session = _mock_session_with_rows([])

    repo = TransacaoRepository(session)
    resultado = await repo.buscar_semantico_multiplos_com_distancia(
        [0.1] * 1536, limite=5, usuario_id=1
    )

    assert resultado == []


@pytest.mark.asyncio
async def test_multiplos_retorna_tuplas_transacao_float():
    t = _make_transacao()
    session = _mock_session_with_rows([(t, 0.75)])

    repo = TransacaoRepository(session)
    resultado = await repo.buscar_semantico_multiplos_com_distancia(
        [0.1] * 1536, limite=5, usuario_id=1
    )

    assert len(resultado) == 1
    transacao, dist = resultado[0]
    assert transacao is t
    assert isinstance(dist, float)
    assert dist == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# Assinatura de buscar_semantico_com_distancia permanece inalterada
# ---------------------------------------------------------------------------


def test_assinatura_buscar_semantico_com_distancia_inalterada():
    sig = inspect.signature(TransacaoRepository.buscar_semantico_com_distancia)
    params = list(sig.parameters.keys())
    # assinatura original: self, embedding, limite=1, usuario_id=None
    assert "embedding" in params
    assert "limite" in params
    assert "usuario_id" in params
    assert sig.parameters["limite"].default == 1
    assert sig.parameters["usuario_id"].default is None


@pytest.mark.asyncio
async def test_buscar_semantico_com_distancia_usa_first():
    """Método original ainda usa .first() e retorna tupla única ou None."""
    mock_result = MagicMock()
    mock_result.first.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = TransacaoRepository(session)
    resultado = await repo.buscar_semantico_com_distancia([0.1] * 1536)

    mock_result.first.assert_called_once()
    assert resultado is None


# ---------------------------------------------------------------------------
# Adapter em agent/entrypoint/_adapter_repo.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adapter_expoe_metodo_novo_com_usuario_id_fixo():
    """O adapter deve repassar usuario_id fixo ao chamar o método do repository."""
    from agent.entrypoint._adapter_repo import AdapterRepo  # importação adiada

    mock_repo = MagicMock()
    mock_repo.buscar_semantico_multiplos_com_distancia = AsyncMock(return_value=[])

    adapter = AdapterRepo(repo=mock_repo, usuario_id=42)
    embedding = [0.1] * 1536
    await adapter.buscar_semantico_multiplos_com_distancia(embedding, limite=5)

    mock_repo.buscar_semantico_multiplos_com_distancia.assert_awaited_once_with(
        embedding, limite=5, usuario_id=42
    )


@pytest.mark.asyncio
async def test_adapter_com_session_factory():
    """Adapter baseado em session_factory cria sessão, instancia repo e chama o método."""
    from agent.entrypoint._adapter_repo import SessionFactoryAdapterRepo  # importação adiada

    t = _make_transacao(usuario_id=7)
    mock_repo_instance = MagicMock()
    mock_repo_instance.buscar_semantico_multiplos_com_distancia = AsyncMock(
        return_value=[(t, 0.3)]
    )

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=MagicMock())
    session_cm.__aexit__ = AsyncMock(return_value=False)

    session_factory = MagicMock(return_value=session_cm)

    with MagicMock() as patch_repo:
        import unittest.mock as um

        with um.patch(
            "agent.entrypoint._adapter_repo.TransacaoRepository",
            return_value=mock_repo_instance,
        ):
            adapter = SessionFactoryAdapterRepo(
                session_factory=session_factory, usuario_id=7
            )
            embedding = [0.2] * 1536
            resultado = await adapter.buscar_semantico_multiplos_com_distancia(
                embedding, limite=3
            )

    assert resultado == [(t, 0.3)]
    mock_repo_instance.buscar_semantico_multiplos_com_distancia.assert_awaited_once_with(
        embedding, limite=3, usuario_id=7
    )
