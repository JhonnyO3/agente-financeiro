"""Testes para a tela de cadastro de usuário (blueprint admin_usuarios)."""

import os
import json
from unittest.mock import MagicMock

import httpx

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("BACKEND_URL", "http://testbackend")

from frontend.app import create_app  # noqa: E402
from frontend.config import Settings  # noqa: E402


def _fake_response(status_code: int, body: dict | None = None) -> httpx.Response:
    content = json.dumps(body or {}).encode()
    return httpx.Response(status_code, content=content)


def _make_app(mock_client: MagicMock):
    settings = Settings(secret_key="test-secret", backend_url="http://testbackend")
    app = create_app(settings)
    app.config["BACKEND_CLIENT"] = mock_client
    return app


def _sessao_admin(client):
    with client.session_transaction() as sess:
        sess["access_token"] = "tok-admin"
        sess["refresh_token"] = "ref-admin"
        sess["role"] = "ADMIN"
        sess["email"] = "admin@test.com"


def _sessao_user(client):
    with client.session_transaction() as sess:
        sess["access_token"] = "tok-user"
        sess["refresh_token"] = "ref-user"
        sess["role"] = "USER"
        sess["email"] = "user@test.com"


# ---------------------------------------------------------------------------
# GET /admin/usuarios/novo
# ---------------------------------------------------------------------------


def test_get_form_admin_retorna_200():
    mock_client = MagicMock()
    app = _make_app(mock_client)
    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.get("/admin/usuarios/novo")
    assert resp.status_code == 200
    assert b"form" in resp.data.lower() or b"nome" in resp.data.lower()


def test_get_form_nao_admin_redireciona_para_login():
    mock_client = MagicMock()
    app = _make_app(mock_client)
    with app.test_client() as c:
        _sessao_user(c)
        resp = c.get("/admin/usuarios/novo")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_get_form_sem_sessao_redireciona_para_login():
    mock_client = MagicMock()
    app = _make_app(mock_client)
    with app.test_client() as c:
        resp = c.get("/admin/usuarios/novo")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# POST /admin/usuarios/novo — sucesso 201
# ---------------------------------------------------------------------------


def test_post_valido_chama_criar_usuario_com_username_derivado():
    mock_client = MagicMock()
    mock_client.criar_usuario.return_value = _fake_response(201)
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João Silva",
                "email": "joao@exemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    mock_client.criar_usuario.assert_called_once()
    body = mock_client.criar_usuario.call_args[0][0]
    assert body["username"] == "joao"
    assert body["email"] == "joao@exemplo.com"
    assert body["nome"] == "João Silva"
    assert body["telefone"] == "5511999998888"
    assert body["senha"] == "segredo123"
    assert body["role"] == "USER"


def test_post_valido_201_redireciona_para_dashboard():
    mock_client = MagicMock()
    mock_client.criar_usuario.return_value = _fake_response(201)
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João Silva",
                "email": "joao@exemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    assert resp.status_code == 302
    assert "/" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# POST /admin/usuarios/novo — 409 preserva campos
# ---------------------------------------------------------------------------


def test_post_409_exibe_erro_email_duplicado():
    mock_client = MagicMock()
    mock_client.criar_usuario.return_value = _fake_response(409)
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João Silva",
                "email": "joao@exemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    assert resp.status_code == 200
    assert (
        "e-mail já está cadastrado" in resp.data.decode().lower()
        or "e-mail já cadastrado" in resp.data.decode().lower()
        or "já está cadastrado" in resp.data.decode().lower()
    )


def test_post_409_preserva_nome_e_telefone():
    mock_client = MagicMock()
    mock_client.criar_usuario.return_value = _fake_response(409)
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João Silva",
                "email": "joao@exemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    body = resp.data.decode()
    assert "João Silva" in body
    assert "5511999998888" in body


def test_post_409_nao_reexibe_senha():
    mock_client = MagicMock()
    mock_client.criar_usuario.return_value = _fake_response(409)
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João Silva",
                "email": "joao@exemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    assert "segredo123" not in resp.data.decode()


# ---------------------------------------------------------------------------
# POST — validações locais (não chama o backend)
# ---------------------------------------------------------------------------


def test_post_email_sem_arroba_nao_chama_backend():
    mock_client = MagicMock()
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João",
                "email": "joaoexemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    mock_client.criar_usuario.assert_not_called()
    assert resp.status_code == 200


def test_post_telefone_nao_numerico_nao_chama_backend():
    mock_client = MagicMock()
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João",
                "email": "joao@exemplo.com",
                "telefone": "(11) abc",
                "senha": "segredo123",
            },
        )

    mock_client.criar_usuario.assert_not_called()
    assert resp.status_code == 200


def test_post_telefone_muito_curto_nao_chama_backend():
    mock_client = MagicMock()
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João",
                "email": "joao@exemplo.com",
                "telefone": "123456789",  # 9 dígitos — menor que 10
                "senha": "segredo123",
            },
        )

    mock_client.criar_usuario.assert_not_called()
    assert resp.status_code == 200


def test_post_nome_vazio_nao_chama_backend():
    mock_client = MagicMock()
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "",
                "email": "joao@exemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    mock_client.criar_usuario.assert_not_called()
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST — 422 e erro httpx
# ---------------------------------------------------------------------------


def test_post_422_exibe_dados_invalidos():
    mock_client = MagicMock()
    mock_client.criar_usuario.return_value = _fake_response(422)
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João",
                "email": "joao@exemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    assert resp.status_code == 200
    assert "dados inválidos" in resp.data.decode().lower()


def test_post_erro_httpx_exibe_backend_indisponivel():
    mock_client = MagicMock()
    mock_client.criar_usuario.side_effect = httpx.HTTPError("connection error")
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        resp = c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "João",
                "email": "joao@exemplo.com",
                "telefone": "5511999998888",
                "senha": "segredo123",
            },
        )

    assert resp.status_code == 200
    assert "backend indisponível" in resp.data.decode().lower()


# ---------------------------------------------------------------------------
# username derivado = parte antes do @
# ---------------------------------------------------------------------------


def test_username_e_parte_antes_do_arroba():
    mock_client = MagicMock()
    mock_client.criar_usuario.return_value = _fake_response(201)
    app = _make_app(mock_client)

    with app.test_client() as c:
        _sessao_admin(c)
        c.post(
            "/admin/usuarios/novo",
            data={
                "nome": "Ana",
                "email": "ana.costa@dominio.org",
                "telefone": "5521988887777",
                "senha": "xpto",
            },
        )

    body = mock_client.criar_usuario.call_args[0][0]
    assert body["username"] == "ana.costa"
