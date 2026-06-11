import json
from unittest.mock import MagicMock

import httpx
import pytest

from frontend.app import create_app
from frontend.config import Settings
from frontend.services.backend_client import BackendClient


def _resposta(status: int, payload, content_type: str = "application/json"):
    resposta = MagicMock(spec=httpx.Response)
    resposta.status_code = status
    resposta.content = json.dumps(payload).encode()
    resposta.headers = {"content-type": content_type}
    resposta.json = lambda: payload
    return resposta


@pytest.fixture
def settings():
    return Settings(
        backend_url="http://backend.test",
        frontend_port=5000,
        secret_key="test-secret",
    )


@pytest.fixture
def backend():
    return MagicMock()


@pytest.fixture
def app(settings, backend):
    app = create_app(settings)
    app.config["BACKEND_CLIENT"] = backend
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _logar(client, access="token-valido", refresh="refresh-valido"):
    with client.session_transaction() as sessao:
        sessao["access_token"] = access
        sessao["refresh_token"] = refresh
        sessao["role"] = "USER"
        sessao["email"] = "alice@example.com"


# ---------------------------------------------------------------------------
# Config / boot
# ---------------------------------------------------------------------------


def test_boot_falha_sem_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(Exception):
        Settings(_env_file=None)


def test_app_define_secret_key_e_cookie_seguro(app):
    assert app.secret_key == "test-secret"
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


# ---------------------------------------------------------------------------
# Proteção de rotas — before_request
# ---------------------------------------------------------------------------


def test_dashboard_sem_login_redireciona_para_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_api_sem_login_retorna_401_json(client, backend):
    resp = client.get("/api/transacoes")
    assert resp.status_code == 401
    assert resp.is_json
    backend.listar_transacoes.assert_not_called()


def test_login_get_e_publico(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"login" in resp.data.lower() or b"senha" in resp.data.lower()


def test_logout_e_isento(client):
    resp = client.post("/logout")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_health_e_isento(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_estaticos_isentos(client):
    resp = client.get("/static/css/app.css")
    assert resp.status_code != 302


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_correto_grava_tokens_e_redireciona(client, backend):
    backend.login.return_value = _resposta(
        200,
        {
            "access_token": "acc",
            "refresh_token": "ref",
            "token_type": "bearer",
            "role": "USER",
        },
    )

    resp = client.post(
        "/login", data={"email": "alice@example.com", "senha": "senha-alice"}
    )

    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    backend.login.assert_called_once_with("alice@example.com", "senha-alice")
    with client.session_transaction() as sessao:
        assert sessao["access_token"] == "acc"
        assert sessao["refresh_token"] == "ref"
        assert sessao["role"] == "USER"
        assert sessao["email"] == "alice@example.com"


def test_login_errado_reabre_modal_com_erro_sem_token(client, backend):
    backend.login.return_value = _resposta(401, {"erro": "credenciais inválidas"})

    resp = client.post("/login", data={"email": "alice@example.com", "senha": "errada"})

    assert resp.status_code in (200, 401)
    assert b"erro" in resp.data.lower() or b"inv" in resp.data.lower()
    with client.session_transaction() as sessao:
        assert "access_token" not in sessao


def test_nao_existe_rota_de_cadastro(client):
    _logar(client)
    assert client.get("/cadastro").status_code == 404
    assert client.get("/register").status_code == 404


def test_pagina_login_nao_tem_formulario_de_cadastro(client):
    resp = client.get("/login")
    corpo = resp.data.lower()
    assert b"cadastr" not in corpo
    assert b"criar conta" not in corpo


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_chama_backend_e_limpa_sessao(client, backend):
    backend.logout.return_value = _resposta(200, {"ok": True})
    _logar(client, refresh="refresh-alice")

    resp = client.post("/logout")

    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    backend.logout.assert_called_once_with("refresh-alice")
    with client.session_transaction() as sessao:
        assert "access_token" not in sessao


def test_logout_best_effort_quando_backend_falha(client, backend):
    backend.logout.side_effect = httpx.ConnectError("down")
    _logar(client)

    resp = client.post("/logout")

    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    with client.session_transaction() as sessao:
        assert "access_token" not in sessao


# ---------------------------------------------------------------------------
# BackendClient — Bearer + refresh
# ---------------------------------------------------------------------------


def _http_client_mock(respostas):
    chamadas = []
    transporte = MagicMock()

    def _request(method, url, **kwargs):
        chamadas.append((method, url, kwargs))
        return respostas.pop(0)

    transporte.request.side_effect = _request
    transporte.__enter__ = lambda self: transporte
    transporte.__exit__ = lambda *a: False
    return transporte, chamadas


def test_backend_client_injeta_bearer(app, monkeypatch):
    cliente = BackendClient(base_url="http://backend.test")
    transporte, chamadas = _http_client_mock([_resposta(200, {"ok": True})])
    monkeypatch.setattr(cliente, "_client", lambda: transporte)

    with app.test_request_context("/"):
        from flask import session

        session["access_token"] = "token-valido"
        session["refresh_token"] = "ref"
        cliente.listar_transacoes({"periodo": "tudo"})

    _, _, kwargs = chamadas[0]
    assert kwargs["headers"]["Authorization"] == "Bearer token-valido"


def test_backend_client_401_com_refresh_valido_renova_e_refaz(app, monkeypatch):
    cliente = BackendClient(base_url="http://backend.test")
    respostas = [
        _resposta(401, {"erro": "não autenticado"}),
        _resposta(
            200, {"access_token": "novo-acc", "refresh_token": "novo-ref"}
        ),
        _resposta(200, {"dados": "ok"}),
    ]
    transporte, chamadas = _http_client_mock(respostas)
    monkeypatch.setattr(cliente, "_client", lambda: transporte)

    with app.test_request_context("/"):
        from flask import session

        session["access_token"] = "expirado"
        session["refresh_token"] = "refresh-valido"
        resp = cliente.listar_transacoes({"periodo": "tudo"})

        assert resp.status_code == 200
        assert session["access_token"] == "novo-acc"
        assert session["refresh_token"] == "novo-ref"

    metodos = [c[0] for c in chamadas]
    urls = [c[1] for c in chamadas]
    assert metodos == ["GET", "POST", "GET"]
    assert "/auth/refresh" in urls[1]
    assert chamadas[2][2]["headers"]["Authorization"] == "Bearer novo-acc"


def test_backend_client_refresh_invalido_limpa_sessao(app, monkeypatch):
    cliente = BackendClient(base_url="http://backend.test")
    respostas = [
        _resposta(401, {"erro": "não autenticado"}),
        _resposta(401, {"erro": "refresh inválido"}),
    ]
    transporte, chamadas = _http_client_mock(respostas)
    monkeypatch.setattr(cliente, "_client", lambda: transporte)

    with app.test_request_context("/"):
        from flask import session

        session["access_token"] = "expirado"
        session["refresh_token"] = "revogado"
        resp = cliente.listar_transacoes({"periodo": "tudo"})

        assert resp.status_code == 401
        assert "access_token" not in session

    assert len(chamadas) == 2


def test_backend_client_401_persistente_nao_faz_loop(app, monkeypatch):
    cliente = BackendClient(base_url="http://backend.test")
    respostas = [
        _resposta(401, {"erro": "não autenticado"}),
        _resposta(200, {"access_token": "novo-acc", "refresh_token": "novo-ref"}),
        _resposta(401, {"erro": "não autenticado"}),
    ]
    transporte, chamadas = _http_client_mock(respostas)
    monkeypatch.setattr(cliente, "_client", lambda: transporte)

    with app.test_request_context("/"):
        from flask import session

        session["access_token"] = "expirado"
        session["refresh_token"] = "refresh-valido"
        resp = cliente.listar_transacoes({"periodo": "tudo"})

        assert resp.status_code == 401
        assert "access_token" not in session

    assert len(chamadas) == 3
