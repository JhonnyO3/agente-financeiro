import os

for var, valor in {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test",
    "JWT_SECRET": "test-secret",
    "JWT_ACCESS_EXPIRES_MIN": "30",
    "JWT_REFRESH_EXPIRES_DAYS": "7",
    "ADMIN_EMAILS": "admin@exemplo.com",
}.items():
    os.environ.setdefault(var, valor)

import datetime
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth import jwt as jwt_module
from backend.auth.dependencies import instalar_handlers
from backend.auth.hashing import hash_senha


def _agora():
    return datetime.datetime.now(datetime.timezone.utc)


def _make_usuario(
    id=1,
    nome="Alice",
    username="alice",
    email="alice@example.com",
    telefone="5511999998888",
    role="USER",
    ativo=True,
):
    criado_em = datetime.datetime(2024, 1, 15, 10, 0, 0, tzinfo=datetime.timezone.utc)
    return SimpleNamespace(
        id=id,
        nome=nome,
        username=username,
        email=email,
        senha_hash=hash_senha("senha"),
        telefone=telefone,
        role=SimpleNamespace(value=role),
        ativo=ativo,
        criado_em=criado_em,
    )


class _FakeSessao:
    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, *args):
        return False


def _bearer(usuario_id=1, role="USER", email="alice@example.com"):
    token = jwt_module.emitir_access(usuario_id=usuario_id, role=role, email=email)
    return {"Authorization": f"Bearer {token}"}


def _cliente_identidade(usuario_retornado):
    """
    Monta TestClient com o router /auth e mocka sessionmaker + repo.
    usuario_retornado: o que buscar_por_telefone devolve (Usuario ou None).
    """
    from backend.controllers import auth as auth_controller

    app = FastAPI()
    instalar_handlers(app)
    app.state.refresh_store = SimpleNamespace(registrar=lambda *a: None)
    app.state.sessionmaker = SimpleNamespace()
    app.include_router(auth_controller.router)

    repo_mock = SimpleNamespace(
        buscar_por_telefone=AsyncMock(return_value=usuario_retornado),
    )

    stack = ExitStack()
    stack.enter_context(
        patch.object(auth_controller, "_usuario_repo", lambda session: repo_mock)
    )
    stack.enter_context(
        patch.object(auth_controller, "_abrir_sessao", lambda request: _FakeSessao())
    )
    return TestClient(app), stack


# ---------------------------------------------------------------------------
# Cenário: telefone de usuário ativo → 200 com UsuarioResponse
# ---------------------------------------------------------------------------


def test_identidade_ativo_retorna_200_com_corpo():
    usuario = _make_usuario(ativo=True)
    client, stack = _cliente_identidade(usuario)
    with stack:
        resp = client.get(
            "/auth/identidade/por-telefone/5511999998888",
            headers=_bearer(),
        )

    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["id"] == 1
    assert corpo["nome"] == "Alice"
    assert corpo["email"] == "alice@example.com"
    assert corpo["telefone"] == "5511999998888"
    assert corpo["ativo"] is True


# ---------------------------------------------------------------------------
# Cenário: telefone de usuário inativo → 204 sem corpo
# ---------------------------------------------------------------------------


def test_identidade_inativo_retorna_204():
    # buscar_por_telefone já filtra ativo=True, então devolve None para inativo
    client, stack = _cliente_identidade(None)
    with stack:
        resp = client.get(
            "/auth/identidade/por-telefone/5511999998888",
            headers=_bearer(),
        )

    assert resp.status_code == 204
    assert resp.content == b""


# ---------------------------------------------------------------------------
# Cenário: telefone inexistente → 204 sem corpo
# ---------------------------------------------------------------------------


def test_identidade_inexistente_retorna_204():
    client, stack = _cliente_identidade(None)
    with stack:
        resp = client.get(
            "/auth/identidade/por-telefone/5511000000000",
            headers=_bearer(),
        )

    assert resp.status_code == 204
    assert resp.content == b""


# ---------------------------------------------------------------------------
# Cenário: inativo e inexistente são indistinguíveis (ambos 204)
# ---------------------------------------------------------------------------


def test_identidade_inativo_e_inexistente_sao_indistinguiveis():
    # Inativo: repo retorna None (filtra ativo=True)
    client_inativo, stack_inativo = _cliente_identidade(None)
    with stack_inativo:
        resp_inativo = client_inativo.get(
            "/auth/identidade/por-telefone/5511999998888",
            headers=_bearer(),
        )

    # Inexistente: repo também retorna None
    client_inex, stack_inex = _cliente_identidade(None)
    with stack_inex:
        resp_inex = client_inex.get(
            "/auth/identidade/por-telefone/5511000000000",
            headers=_bearer(),
        )

    assert resp_inativo.status_code == 204
    assert resp_inex.status_code == 204
    assert resp_inativo.content == resp_inex.content


# ---------------------------------------------------------------------------
# Cenário: sem autenticação → 401
# ---------------------------------------------------------------------------


def test_identidade_sem_auth_retorna_401():
    client, stack = _cliente_identidade(None)
    with stack:
        resp = client.get("/auth/identidade/por-telefone/5511999998888")

    assert resp.status_code == 401
    assert resp.json() == {"erro": "não autenticado"}


def test_identidade_token_invalido_retorna_401():
    client, stack = _cliente_identidade(None)
    with stack:
        resp = client.get(
            "/auth/identidade/por-telefone/5511999998888",
            headers={"Authorization": "Bearer token-invalido"},
        )

    assert resp.status_code == 401
    assert resp.json() == {"erro": "não autenticado"}
