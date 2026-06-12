import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_API_KEY", "test")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "+5511999990001")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Jhonatas")
os.environ.setdefault("WEBHOOK_APIKEY", "test-apikey")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "test@exemplo.com")

from contextlib import asynccontextmanager
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

USUARIO_ID = 42


def _build_wrapper():
    repo = MagicMock()
    repo.buscar_por_id = AsyncMock(return_value=None)
    repo.buscar_por_grupo = AsyncMock(return_value=[])
    repo.buscar_semantico = AsyncMock(return_value=[])
    repo.buscar_semantico_com_distancia = AsyncMock(return_value=None)
    repo.listar_por_periodo = AsyncMock(return_value=[])
    repo.listar_por_periodo_com_embedding = AsyncMock(return_value=[])
    repo.agregar_por_categoria = AsyncMock(return_value=[])
    repo.excluir = AsyncMock(return_value=None)
    repo.excluir_grupo = AsyncMock(return_value=0)
    repo.excluir_por_filtros = AsyncMock(return_value=0)
    repo.contar_por_filtros = AsyncMock(return_value=0)
    repo.atualizar = AsyncMock(return_value=MagicMock())

    session = MagicMock()

    @asynccontextmanager
    async def _ctx():
        yield session

    class _Factory:
        def __call__(self):
            return _ctx()

        def begin(self):
            return _ctx()

    from agent.entrypoint.main import _SessionFactoryRepository

    wrapper = _SessionFactoryRepository(_Factory(), USUARIO_ID)
    wrapper._repo = lambda _session: repo
    return wrapper, repo


@pytest.mark.asyncio
async def test_buscar_por_id_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.buscar_por_id(7)
    repo.buscar_por_id.assert_awaited_once_with(7, usuario_id=USUARIO_ID)


@pytest.mark.asyncio
async def test_buscar_por_grupo_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    grupo = uuid4()
    await wrapper.buscar_por_grupo(grupo)
    repo.buscar_por_grupo.assert_awaited_once_with(grupo, usuario_id=USUARIO_ID)


@pytest.mark.asyncio
async def test_buscar_semantico_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.buscar_semantico([0.1] * 1536, 5)
    repo.buscar_semantico.assert_awaited_once_with([0.1] * 1536, 5, usuario_id=USUARIO_ID)


@pytest.mark.asyncio
async def test_buscar_semantico_com_distancia_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.buscar_semantico_com_distancia([0.1] * 1536, 1)
    repo.buscar_semantico_com_distancia.assert_awaited_once_with(
        [0.1] * 1536, 1, usuario_id=USUARIO_ID
    )


@pytest.mark.asyncio
async def test_listar_por_periodo_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.listar_por_periodo(date(2026, 1, 1), date(2026, 1, 31))
    repo.listar_por_periodo.assert_awaited_once_with(
        date(2026, 1, 1), date(2026, 1, 31), usuario_id=USUARIO_ID
    )


@pytest.mark.asyncio
async def test_listar_por_periodo_com_embedding_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.listar_por_periodo_com_embedding(date(2026, 1, 1), date(2026, 1, 31))
    repo.listar_por_periodo_com_embedding.assert_awaited_once_with(
        date(2026, 1, 1), date(2026, 1, 31), usuario_id=USUARIO_ID
    )


@pytest.mark.asyncio
async def test_agregar_por_categoria_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.agregar_por_categoria(date(2026, 1, 1), date(2026, 1, 31))
    repo.agregar_por_categoria.assert_awaited_once_with(
        date(2026, 1, 1), date(2026, 1, 31), usuario_id=USUARIO_ID
    )


@pytest.mark.asyncio
async def test_atualizar_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    dados = MagicMock()
    await wrapper.atualizar(7, dados)
    repo.atualizar.assert_awaited_once_with(7, dados, usuario_id=USUARIO_ID)


@pytest.mark.asyncio
async def test_excluir_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.excluir(7)
    repo.excluir.assert_awaited_once_with(7, usuario_id=USUARIO_ID)


@pytest.mark.asyncio
async def test_excluir_grupo_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    grupo = uuid4()
    await wrapper.excluir_grupo(grupo)
    repo.excluir_grupo.assert_awaited_once_with(grupo, usuario_id=USUARIO_ID)


@pytest.mark.asyncio
async def test_excluir_por_filtros_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.excluir_por_filtros(date(2026, 1, 1), date(2026, 1, 31), "ALIMENTACAO")
    repo.excluir_por_filtros.assert_awaited_once_with(
        date(2026, 1, 1), date(2026, 1, 31), "ALIMENTACAO", usuario_id=USUARIO_ID
    )


@pytest.mark.asyncio
async def test_contar_por_filtros_injeta_usuario_id():
    wrapper, repo = _build_wrapper()
    await wrapper.contar_por_filtros(date(2026, 1, 1), date(2026, 1, 31), None)
    repo.contar_por_filtros.assert_awaited_once_with(
        date(2026, 1, 1), date(2026, 1, 31), None, usuario_id=USUARIO_ID
    )


# ---------------------------------------------------------------------------
# resolver_usuario_id — fail-fast se email não encontrado
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_lifespan_resolve_usuario_id_por_email():
    from types import SimpleNamespace
    from agent.entrypoint.main import resolver_usuario_id

    usuario = SimpleNamespace(id=1, email="test@exemplo.com")
    usuario_repo = MagicMock()
    usuario_repo.buscar_por_email = AsyncMock(return_value=usuario)

    resolved = await resolver_usuario_id(usuario_repo, "test@exemplo.com")

    usuario_repo.buscar_por_email.assert_awaited_once_with("test@exemplo.com")
    assert resolved == 1


@pytest.mark.asyncio
async def test_lifespan_falha_explicita_se_email_nao_existe():
    import pytest
    from agent.entrypoint.main import resolver_usuario_id

    usuario_repo = MagicMock()
    usuario_repo.buscar_por_email = AsyncMock(return_value=None)

    with pytest.raises(RuntimeError, match="test@exemplo.com"):
        await resolver_usuario_id(usuario_repo, "test@exemplo.com")
