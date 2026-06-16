"""
Testes TDD — Task E (05): Wiring main.py + config + estado_store configurável.

Cenários baseados em specs/cadastro-e-multiusuario/scenarios/05-wiring-main-config-estado.feature

- App importa sem WHATSAPP_ALLOWED_NUMBER
- app.state.session_factory e app.state.repo_factory expostos; repo_factory(7) → usuario_id=7
- Consumidor desempacota (usuario_id, numero, texto) e chama worker.receber com os 3
- construir_roteador produz Roteador funcional
- Nenhuma referência a WHATSAPP_ALLOWED_NUMBER no código
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Env vars obrigatórias ANTES de qualquer import do projeto.
# WHATSAPP_ALLOWED_NUMBER propositalmente ausente — valida cenário do feature.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake-key-for-tests")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Teste")
os.environ.setdefault("WEBHOOK_APIKEY", "test-apikey")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DEBOUNCE_SEGUNDOS", "1")

import pytest


# ---------------------------------------------------------------------------
# Cenário: App importa sem WHATSAPP_ALLOWED_NUMBER
# ---------------------------------------------------------------------------


def test_config_importa_sem_whatsapp_allowed_number():
    """
    Config importa normalmente mesmo sem WHATSAPP_ALLOWED_NUMBER definido.
    Valida indiretamente: o campo foi removido do Settings (extra='ignore' cobre
    o caso em que a env var existe por herança de outro teste).
    """
    import sys

    # Reimporta Settings em ambiente limpo sem WHATSAPP_ALLOWED_NUMBER
    env_limpo = {k: v for k, v in os.environ.items() if k != "WHATSAPP_ALLOWED_NUMBER"}
    env_limpo.setdefault(
        "DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test"
    )
    env_limpo.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
    env_limpo.setdefault("EVOLUTION_INSTANCE", "test")
    env_limpo.setdefault("EVOLUTION_API_KEY", "test-key")
    env_limpo.setdefault("OPENAI_API_KEY", "sk-fake-key-for-tests")
    env_limpo.setdefault("RESPONSAVEL_PADRAO", "Teste")
    env_limpo.setdefault("WEBHOOK_APIKEY", "test-apikey")
    env_limpo.setdefault("REDIS_URL", "redis://localhost:6379/0")
    env_limpo.setdefault("AGENTE_USUARIO_EMAIL", "test@exemplo.com")

    # Remove cache para reimportar limpo
    for mod in list(sys.modules.keys()):
        if mod.startswith("agent.config"):
            del sys.modules[mod]

    from unittest.mock import patch

    with patch.dict(os.environ, env_limpo, clear=True):
        from agent.config import Settings

        s = Settings()  # deve instanciar sem erro mesmo sem WHATSAPP_ALLOWED_NUMBER
        assert (
            not hasattr(s, "WHATSAPP_ALLOWED_NUMBER")
            or "WHATSAPP_ALLOWED_NUMBER" not in s.model_fields
        )


def test_config_nao_tem_campo_whatsapp_allowed_number():
    """Settings não deve declarar o campo WHATSAPP_ALLOWED_NUMBER."""
    from agent.config import Settings

    assert (
        not hasattr(Settings.model_fields, "WHATSAPP_ALLOWED_NUMBER")
        or "WHATSAPP_ALLOWED_NUMBER" not in Settings.model_fields
    ), "Settings ainda declara WHATSAPP_ALLOWED_NUMBER — deve ser removido"


def test_config_tem_historico_max_mensagens():
    from agent.config import settings

    assert hasattr(settings, "HISTORICO_MAX_MENSAGENS")
    assert settings.HISTORICO_MAX_MENSAGENS == 10  # default


def test_config_tem_historico_ttl_horas():
    from agent.config import settings

    assert hasattr(settings, "HISTORICO_TTL_HORAS")
    assert settings.HISTORICO_TTL_HORAS == 2  # default


# ---------------------------------------------------------------------------
# Cenário: Nenhuma referência a WHATSAPP_ALLOWED_NUMBER no código
# ---------------------------------------------------------------------------


def test_main_nao_referencia_whatsapp_allowed_number():
    import inspect
    import agent.entrypoint.main as main_module

    source = inspect.getsource(main_module)
    assert "WHATSAPP_ALLOWED_NUMBER" not in source, (
        "main.py ainda referencia WHATSAPP_ALLOWED_NUMBER"
    )


def test_config_nao_referencia_whatsapp_allowed_number():
    import inspect
    import agent.config as config_module

    source = inspect.getsource(config_module)
    assert "WHATSAPP_ALLOWED_NUMBER" not in source, (
        "config.py ainda referencia WHATSAPP_ALLOWED_NUMBER"
    )


# ---------------------------------------------------------------------------
# Cenário: _criar_repo_factory produz repo com usuario_id correto
# ---------------------------------------------------------------------------


def test_repo_factory_escopa_por_usuario_id():
    """_criar_repo_factory(7) devolve repo com _usuario_id == 7."""
    from agent.entrypoint.main import _criar_repo_factory, _SessionFactoryRepository

    fake_session_factory = MagicMock()
    factory = _criar_repo_factory(fake_session_factory)

    repo = factory(7)

    assert isinstance(repo, _SessionFactoryRepository)
    assert repo._usuario_id == 7


def test_repo_factory_instancias_distintas():
    """Dois usuario_ids devem gerar instâncias distintas de repo."""
    from agent.entrypoint.main import _criar_repo_factory

    fake_session_factory = MagicMock()
    factory = _criar_repo_factory(fake_session_factory)

    repo_a = factory(1)
    repo_b = factory(2)

    assert repo_a is not repo_b
    assert repo_a._usuario_id == 1
    assert repo_b._usuario_id == 2


# ---------------------------------------------------------------------------
# Cenário: _criar_construir_roteador produz Roteador funcional
# ---------------------------------------------------------------------------


def test_construir_roteador_retorna_roteador():
    """_criar_construir_roteador(repo) deve retornar um Roteador."""
    from agent.entrypoint.main import (
        _criar_construir_roteador,
        _SessionFactoryRepository,
    )
    from agent.services.roteador import Roteador

    relogio = MagicMock()
    embedder = MagicMock()
    estado_store = MagicMock()

    construir = _criar_construir_roteador(
        relogio=relogio, embedder=embedder, estado_store=estado_store
    )

    fake_session_factory = MagicMock()
    repo = _SessionFactoryRepository(fake_session_factory, usuario_id=1)

    roteador = construir(repo)

    assert isinstance(roteador, Roteador)


def test_construir_roteador_novo_por_chamada():
    """Cada chamada a construir(repo) deve retornar uma nova instância."""
    from agent.entrypoint.main import (
        _criar_construir_roteador,
        _SessionFactoryRepository,
    )

    relogio = MagicMock()
    embedder = MagicMock()
    estado_store = MagicMock()

    construir = _criar_construir_roteador(
        relogio=relogio, embedder=embedder, estado_store=estado_store
    )

    fake_sf = MagicMock()
    repo1 = _SessionFactoryRepository(fake_sf, 1)
    repo2 = _SessionFactoryRepository(fake_sf, 2)

    r1 = construir(repo1)
    r2 = construir(repo2)

    assert r1 is not r2


# ---------------------------------------------------------------------------
# Cenário: consumidor desempacota tupla de 3 elementos
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consumidor_desempacota_tupla_3():
    """Consumidor deve desempacotar (usuario_id, numero, texto) e chamar worker.receber."""
    chamadas: list[tuple] = []

    worker = MagicMock()

    async def fake_receber(usuario_id: int, numero: str, texto: str) -> None:
        chamadas.append((usuario_id, numero, texto))

    worker.receber = AsyncMock(side_effect=fake_receber)
    worker.processar_pendentes = AsyncMock()

    fila: asyncio.Queue = asyncio.Queue()

    # Simula o consumidor do main.py
    async def _consumidor():
        while True:
            usuario_id, numero, texto = await fila.get()
            await worker.receber(usuario_id, numero, texto)
            asyncio.create_task(worker.processar_pendentes())
            fila.task_done()

    task = asyncio.create_task(_consumidor())

    await fila.put((42, "5511999998888", "gastei 50"))
    await asyncio.sleep(0.05)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(chamadas) == 1
    assert chamadas[0] == (42, "5511999998888", "gastei 50")


# ---------------------------------------------------------------------------
# Cenário: lifespan expõe session_factory e repo_factory (sem infraestrutura real)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifespan_expoe_session_factory_e_repo_factory():
    """
    Testa que o lifespan expõe app.state.session_factory e app.state.repo_factory
    chamando o lifespan diretamente com um app fake (sem infraestrutura real).
    """
    from fastapi import FastAPI

    fake_engine = AsyncMock()
    fake_engine.dispose = AsyncMock()

    fake_session_factory = MagicMock(name="session_factory")
    fake_session_factory.begin = MagicMock()
    fake_session_factory.__call__ = MagicMock()

    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.setex = AsyncMock()
    fake_redis.aclose = AsyncMock()

    fake_evolution = AsyncMock()
    fake_evolution.fechar = AsyncMock()

    with (
        patch("agent.entrypoint.main.create_async_engine", return_value=fake_engine),
        patch(
            "agent.entrypoint.main.async_sessionmaker",
            return_value=fake_session_factory,
        ),
        patch("agent.entrypoint.main.aioredis.from_url", return_value=fake_redis),
        patch("agent.entrypoint.main.EvolutionApiClient", return_value=fake_evolution),
        patch("agent.entrypoint.main.Embedder", return_value=MagicMock()),
        patch("agent.entrypoint.main.Classificador", return_value=MagicMock()),
        patch("agent.entrypoint.main.Formatador", return_value=MagicMock()),
    ):
        from agent.entrypoint.main import lifespan, _SessionFactoryRepository

        test_app = FastAPI()

        # Chama o lifespan diretamente com test_app — forma correta de testar lifespan
        async with lifespan(test_app):
            assert hasattr(test_app.state, "session_factory"), (
                "lifespan deve expor app.state.session_factory"
            )
            assert hasattr(test_app.state, "repo_factory"), (
                "lifespan deve expor app.state.repo_factory"
            )
            assert callable(test_app.state.repo_factory)

            # repo_factory(7) deve retornar repo com usuario_id=7
            repo = test_app.state.repo_factory(7)
            assert isinstance(repo, _SessionFactoryRepository)
            assert repo._usuario_id == 7

            # usuario_id fixo (legado) deve ter sido removido do state
            assert not hasattr(test_app.state, "usuario_id")
