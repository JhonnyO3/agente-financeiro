import logging

from fastapi.testclient import TestClient


def _build_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    from backend.main import app

    return app


def test_health_retorna_ok(monkeypatch):
    app = _build_app(monkeypatch)
    with TestClient(app) as client:
        resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}


def test_engine_criado_uma_vez(monkeypatch):
    app = _build_app(monkeypatch)
    with TestClient(app) as client:
        client.get("/health")
        sessionmaker_apos_1 = app.state.sessionmaker
        engine_apos_1 = app.state.engine
        client.get("/health")
        sessionmaker_apos_2 = app.state.sessionmaker
        engine_apos_2 = app.state.engine
    assert sessionmaker_apos_1 is sessionmaker_apos_2
    assert engine_apos_1 is engine_apos_2


def test_engine_nao_usa_nullpool(monkeypatch):
    from sqlalchemy.pool import NullPool

    app = _build_app(monkeypatch)
    with TestClient(app):
        assert not isinstance(app.state.engine.pool, NullPool)


def test_engine_disposed_no_shutdown(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    import backend.main as main

    disposed = {"chamado": False}
    real_criar_engine = main.criar_engine

    def _criar_engine_spy(url):
        engine = real_criar_engine(url)
        original = engine.sync_engine.dispose

        def _dispose(*args, **kwargs):
            disposed["chamado"] = True
            return original(*args, **kwargs)

        engine.sync_engine.dispose = _dispose
        return engine

    monkeypatch.setattr(main, "criar_engine", _criar_engine_spy)
    with TestClient(main.app):
        pass
    assert disposed["chamado"] is True


def test_log_startup_documenta_gargalo(monkeypatch, caplog):
    app = _build_app(monkeypatch)
    with caplog.at_level(logging.INFO):
        with TestClient(app):
            pass
    mensagens = " ".join(r.getMessage().lower() for r in caplog.records)
    assert "reconex" in mensagens or "request" in mensagens
    assert "pool" in mensagens
