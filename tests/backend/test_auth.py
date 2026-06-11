import os

for var, valor in {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test",
    "JWT_SECRET": "test-secret",
    "JWT_ACCESS_EXPIRES_MIN": "30",
    "JWT_REFRESH_EXPIRES_DAYS": "7",
    "ADMIN_EMAILS": "admin@exemplo.com,jhonatas2004@gmail.com",
}.items():
    os.environ.setdefault(var, valor)

import datetime
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.auth import jwt as jwt_module
from backend.auth.dependencies import (
    UsuarioToken,
    get_admin,
    get_usuario_atual,
    instalar_handlers,
)
from backend.auth.hashing import hash_senha, verificar_senha
from backend.auth.refresh_store import RefreshStore
from backend.config import settings


def _agora():
    return datetime.datetime.now(datetime.timezone.utc)


def make_usuario(
    id=1,
    email="alice@example.com",
    senha="senha-correta",
    role="USER",
    ativo=True,
):
    return SimpleNamespace(
        id=id,
        email=email,
        senha_hash=hash_senha(senha),
        role=SimpleNamespace(value=role),
        ativo=ativo,
        nome="Alice",
        username="alice",
    )


class _FakeSessao:
    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, *args):
        return False


def repo_de(usuario):
    return SimpleNamespace(
        buscar_por_email=AsyncMock(return_value=usuario),
        buscar_por_id=AsyncMock(return_value=usuario),
    )


def cliente_auth(usuario_repo):
    from backend.controllers import auth as auth_controller

    app = FastAPI()
    store = RefreshStore()
    app.state.refresh_store = store
    app.state.sessionmaker = SimpleNamespace()
    app.include_router(auth_controller.router)

    stack = ExitStack()
    stack.enter_context(
        patch.object(auth_controller, "_usuario_repo", lambda session: usuario_repo)
    )
    stack.enter_context(
        patch.object(auth_controller, "_abrir_sessao", lambda request: _FakeSessao())
    )
    return TestClient(app), store, stack


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def test_hash_senha_formato_bcrypt():
    resultado = hash_senha("minha-senha")
    assert resultado.startswith("$2b$")
    assert resultado != "minha-senha"


def test_verificar_senha_correta():
    h = hash_senha("minha-senha")
    assert verificar_senha("minha-senha", h) is True


def test_verificar_senha_incorreta():
    h = hash_senha("minha-senha")
    assert verificar_senha("outra-senha", h) is False


# ---------------------------------------------------------------------------
# jwt module — tokens e claims
# ---------------------------------------------------------------------------


def test_access_token_contem_claims_do_contrato():
    token = jwt_module.emitir_access(usuario_id=7, role="USER", email="a@b.com")
    payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == "7"
    assert payload["role"] == "USER"
    assert payload["email"] == "a@b.com"
    assert payload["type"] == "access"
    assert "exp" in payload


def test_refresh_token_contem_claims_do_contrato():
    token, jti = jwt_module.emitir_refresh(usuario_id=7)
    payload = pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == "7"
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti
    assert "exp" in payload


def test_validar_access_rejeita_type_refresh():
    refresh, _ = jwt_module.emitir_refresh(usuario_id=7)
    with pytest.raises(jwt_module.TokenInvalido):
        jwt_module.validar_access(refresh)


def test_validar_access_rejeita_assinatura_invalida():
    forjado = pyjwt.encode(
        {"sub": "1", "role": "USER", "email": "x@y.com", "type": "access",
         "exp": _agora() + datetime.timedelta(minutes=5)},
        "outro-segredo",
        algorithm="HS256",
    )
    with pytest.raises(jwt_module.TokenInvalido):
        jwt_module.validar_access(forjado)


def test_validar_access_rejeita_expirado():
    expirado = pyjwt.encode(
        {"sub": "1", "role": "USER", "email": "x@y.com", "type": "access",
         "exp": _agora() - datetime.timedelta(minutes=1)},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(jwt_module.TokenInvalido):
        jwt_module.validar_access(expirado)


# ---------------------------------------------------------------------------
# RefreshStore
# ---------------------------------------------------------------------------


def test_refresh_store_registra_e_valida():
    store = RefreshStore()
    exp = _agora() + datetime.timedelta(days=1)
    store.registrar("jti-1", exp)
    assert store.ativo("jti-1") is True


def test_refresh_store_revoga():
    store = RefreshStore()
    exp = _agora() + datetime.timedelta(days=1)
    store.registrar("jti-1", exp)
    store.revogar("jti-1")
    assert store.ativo("jti-1") is False


def test_refresh_store_jti_desconhecido_inativo():
    store = RefreshStore()
    assert store.ativo("nao-existe") is False


def test_refresh_store_expirado_inativo():
    store = RefreshStore()
    exp = _agora() - datetime.timedelta(seconds=1)
    store.registrar("jti-velho", exp)
    assert store.ativo("jti-velho") is False


def test_refresh_store_revogar_idempotente():
    store = RefreshStore()
    store.revogar("inexistente")
    store.revogar("inexistente")


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


def test_login_credenciais_validas_retorna_tokens():
    usuario = make_usuario()
    repo = SimpleNamespace(buscar_por_email=AsyncMock(return_value=usuario))
    client, store, stack = cliente_auth(repo)
    with stack:
        resposta = client.post(
            "/auth/login",
            json={"email": "alice@example.com", "senha": "senha-correta"},
        )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    assert corpo["role"] == "USER"
    access = pyjwt.decode(corpo["access_token"], settings.JWT_SECRET, algorithms=["HS256"])
    assert access["type"] == "access"
    assert access["email"] == "alice@example.com"
    assert access["sub"] == "1"
    refresh = pyjwt.decode(corpo["refresh_token"], settings.JWT_SECRET, algorithms=["HS256"])
    assert refresh["type"] == "refresh"
    assert "jti" in refresh


def test_login_email_caixa_alta_normaliza_para_minusculo():
    usuario = make_usuario()
    repo = SimpleNamespace(buscar_por_email=AsyncMock(return_value=usuario))
    client, store, stack = cliente_auth(repo)
    with stack:
        resposta = client.post(
            "/auth/login",
            json={"email": "  ALICE@Example.com  ", "senha": "senha-correta"},
        )

    assert resposta.status_code == 200
    repo.buscar_por_email.assert_awaited_once_with("alice@example.com")


def test_login_senha_errada_401_generico():
    usuario = make_usuario()
    repo = SimpleNamespace(buscar_por_email=AsyncMock(return_value=usuario))
    client, store, stack = cliente_auth(repo)
    with stack:
        resposta = client.post(
            "/auth/login",
            json={"email": "alice@example.com", "senha": "errada"},
        )

    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "credenciais inválidas"}


def test_login_email_inexistente_401_generico():
    repo = SimpleNamespace(buscar_por_email=AsyncMock(return_value=None))
    client, store, stack = cliente_auth(repo)
    with stack:
        resposta = client.post(
            "/auth/login",
            json={"email": "nao@existe.com", "senha": "qualquer"},
        )

    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "credenciais inválidas"}


def test_login_usuario_inativo_401_generico():
    usuario = make_usuario(email="inativo@example.com", senha="qualquer", ativo=False)
    repo = SimpleNamespace(buscar_por_email=AsyncMock(return_value=usuario))
    client, store, stack = cliente_auth(repo)
    with stack:
        resposta = client.post(
            "/auth/login",
            json={"email": "inativo@example.com", "senha": "qualquer"},
        )

    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "credenciais inválidas"}


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------


def _login(client):
    return client.post(
        "/auth/login",
        json={"email": "alice@example.com", "senha": "senha-correta"},
    ).json()


def test_refresh_valido_rotaciona():
    repo = repo_de(make_usuario())
    client, store, stack = cliente_auth(repo)
    with stack:
        tokens = _login(client)
        resposta = client.post(
            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token_type"] == "bearer"
    antigo = pyjwt.decode(tokens["refresh_token"], settings.JWT_SECRET, algorithms=["HS256"])
    novo = pyjwt.decode(corpo["refresh_token"], settings.JWT_SECRET, algorithms=["HS256"])
    assert novo["jti"] != antigo["jti"]


def test_refresh_jti_anterior_invalido_apos_rotation():
    repo = repo_de(make_usuario())
    client, store, stack = cliente_auth(repo)
    with stack:
        tokens = _login(client)
        client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        resposta = client.post(
            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )

    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "refresh inválido"}


def test_refresh_expirado_401():
    repo = repo_de(make_usuario())
    client, store, stack = cliente_auth(repo)
    expirado = pyjwt.encode(
        {"sub": "1", "type": "refresh", "jti": "x",
         "exp": _agora() - datetime.timedelta(seconds=1)},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    with stack:
        resposta = client.post("/auth/refresh", json={"refresh_token": expirado})

    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "refresh inválido"}


def test_refresh_assinatura_invalida_401():
    repo = repo_de(make_usuario())
    client, store, stack = cliente_auth(repo)
    forjado = pyjwt.encode(
        {"sub": "1", "type": "refresh", "jti": "x",
         "exp": _agora() + datetime.timedelta(days=1)},
        "outro-segredo",
        algorithm="HS256",
    )
    with stack:
        resposta = client.post("/auth/refresh", json={"refresh_token": forjado})

    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "refresh inválido"}


def test_refresh_com_access_token_type_errado_401():
    repo = repo_de(make_usuario())
    client, store, stack = cliente_auth(repo)
    with stack:
        tokens = _login(client)
        resposta = client.post(
            "/auth/refresh", json={"refresh_token": tokens["access_token"]}
        )

    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "refresh inválido"}


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------


def test_logout_revoga_refresh():
    repo = repo_de(make_usuario())
    client, store, stack = cliente_auth(repo)
    with stack:
        tokens = _login(client)
        saida = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
        usado = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    assert saida.status_code == 200
    assert saida.json() == {"ok": True}
    assert usado.status_code == 401


def test_logout_idempotente():
    repo = repo_de(make_usuario())
    client, store, stack = cliente_auth(repo)
    with stack:
        tokens = _login(client)
        client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
        segundo = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    assert segundo.status_code == 200
    assert segundo.json() == {"ok": True}


def test_logout_token_invalido_ainda_200():
    repo = repo_de(make_usuario())
    client, store, stack = cliente_auth(repo)
    with stack:
        resposta = client.post("/auth/logout", json={"refresh_token": "lixo-nao-jwt"})

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Guard get_usuario_atual
# ---------------------------------------------------------------------------


def _app_protegido():
    app = FastAPI()
    instalar_handlers(app)

    @app.get("/protegido")
    async def protegido(usuario: UsuarioToken = Depends(get_usuario_atual)):
        return {"usuario_id": usuario.usuario_id, "role": usuario.role}

    return app


def test_guard_sem_header_401():
    client = TestClient(_app_protegido())
    resposta = client.get("/protegido")
    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "não autenticado"}


def test_guard_bearer_malformado_401():
    client = TestClient(_app_protegido())
    resposta = client.get("/protegido", headers={"Authorization": "Bearer nao-jwt"})
    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "não autenticado"}


def test_guard_sem_prefixo_bearer_401():
    token = jwt_module.emitir_access(usuario_id=1, role="USER", email="a@b.com")
    client = TestClient(_app_protegido())
    resposta = client.get("/protegido", headers={"Authorization": token})
    assert resposta.status_code == 401


def test_guard_access_expirado_401():
    expirado = pyjwt.encode(
        {"sub": "1", "role": "USER", "email": "a@b.com", "type": "access",
         "exp": _agora() - datetime.timedelta(minutes=1)},
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    client = TestClient(_app_protegido())
    resposta = client.get("/protegido", headers={"Authorization": f"Bearer {expirado}"})
    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "não autenticado"}


def test_guard_access_valido_injeta_usuario():
    token = jwt_module.emitir_access(usuario_id=42, role="USER", email="a@b.com")
    client = TestClient(_app_protegido())
    resposta = client.get("/protegido", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 200
    assert resposta.json() == {"usuario_id": 42, "role": "USER"}


def test_guard_refresh_onde_espera_access_401():
    refresh, _ = jwt_module.emitir_refresh(usuario_id=1)
    client = TestClient(_app_protegido())
    resposta = client.get("/protegido", headers={"Authorization": f"Bearer {refresh}"})
    assert resposta.status_code == 401
    assert resposta.json() == {"erro": "não autenticado"}


# ---------------------------------------------------------------------------
# Guard get_admin
# ---------------------------------------------------------------------------


def _app_admin(usuario_repo):
    app = FastAPI()
    instalar_handlers(app)
    app.state.sessionmaker = SimpleNamespace()

    @app.get("/admin/usuarios")
    async def admin(usuario: UsuarioToken = Depends(get_admin)):
        return {"ok": True}

    stack = ExitStack()
    stack.enter_context(
        patch(
            "backend.auth.dependencies.UsuarioRepository",
            lambda session: usuario_repo,
        )
    )
    stack.enter_context(
        patch("backend.auth.dependencies._abrir_sessao", _fake_sessao)
    )
    return TestClient(app), stack


def _fake_sessao(request):
    return _FakeSessao()


def test_admin_aceita_admin_valido():
    usuario_db = make_usuario(id=5, email="admin@exemplo.com", role="ADMIN", ativo=True)
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=usuario_db))
    client, stack = _app_admin(repo)
    token = jwt_module.emitir_access(usuario_id=5, role="ADMIN", email="admin@exemplo.com")
    with stack:
        resposta = client.get("/admin/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 200


def test_admin_rejeita_role_user_403():
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=None))
    client, stack = _app_admin(repo)
    token = jwt_module.emitir_access(usuario_id=1, role="USER", email="admin@exemplo.com")
    with stack:
        resposta = client.get("/admin/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 403
    assert resposta.json() == {"erro": "acesso negado"}


def test_admin_rejeita_email_fora_allowlist_403():
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=None))
    client, stack = _app_admin(repo)
    token = jwt_module.emitir_access(usuario_id=9, role="ADMIN", email="invasor@exemplo.com")
    with stack:
        resposta = client.get("/admin/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 403
    assert resposta.json() == {"erro": "acesso negado"}


def test_admin_rejeita_desativado_no_banco_403():
    usuario_db = make_usuario(id=5, email="admin@exemplo.com", role="ADMIN", ativo=False)
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=usuario_db))
    client, stack = _app_admin(repo)
    token = jwt_module.emitir_access(usuario_id=5, role="ADMIN", email="admin@exemplo.com")
    with stack:
        resposta = client.get("/admin/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 403
    assert resposta.json() == {"erro": "acesso negado"}


def test_admin_rejeita_role_rebaixada_no_banco_403():
    usuario_db = make_usuario(id=5, email="admin@exemplo.com", role="USER", ativo=True)
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=usuario_db))
    client, stack = _app_admin(repo)
    token = jwt_module.emitir_access(usuario_id=5, role="ADMIN", email="admin@exemplo.com")
    with stack:
        resposta = client.get("/admin/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 403
    assert resposta.json() == {"erro": "acesso negado"}


def test_admin_rejeita_usuario_inexistente_no_banco_403():
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=None))
    client, stack = _app_admin(repo)
    token = jwt_module.emitir_access(usuario_id=5, role="ADMIN", email="admin@exemplo.com")
    with stack:
        resposta = client.get("/admin/usuarios", headers={"Authorization": f"Bearer {token}"})

    assert resposta.status_code == 403
    assert resposta.json() == {"erro": "acesso negado"}


# ---------------------------------------------------------------------------
# Config / boot
# ---------------------------------------------------------------------------


def test_boot_sem_jwt_secret_falha():
    from pydantic import ValidationError

    from backend.config import Settings

    ambiente = {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
        "ADMIN_EMAILS": "a@b.com",
    }
    with patch.dict(os.environ, ambiente, clear=True):
        with pytest.raises(ValidationError):
            Settings(_env_file=None)

    with patch.dict(os.environ, {**ambiente, "JWT_SECRET": "x"}, clear=True):
        config = Settings(_env_file=None)
    assert config.JWT_SECRET == "x"
    assert config.ADMIN_EMAILS == {"a@b.com"}


def test_boot_sem_admin_emails_falha():
    from pydantic import ValidationError

    from backend.config import Settings

    ambiente = {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
        "JWT_SECRET": "x",
    }
    with patch.dict(os.environ, ambiente, clear=True):
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
