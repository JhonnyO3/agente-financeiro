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

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.auth.dependencies import HttpErro, UsuarioToken, get_admin, instalar_handlers
from backend.auth.hashing import verificar_senha
from backend.dependencies import get_session, get_session_begin


def make_usuario(
    id=1,
    nome="Alice",
    username="alice",
    email="alice@example.com",
    senha_hash="$2b$hashantigo",
    telefone=None,
    role="USER",
    ativo=True,
):
    return SimpleNamespace(
        id=id,
        nome=nome,
        username=username,
        email=email,
        senha_hash=senha_hash,
        telefone=telefone,
        role=SimpleNamespace(value=role),
        ativo=ativo,
        criado_em=datetime.datetime(2026, 1, 1, 12, 0, 0),
    )


def make_transacao(id, usuario_id=2, dia=1, valor="10.00"):
    from decimal import Decimal

    return SimpleNamespace(
        id=id,
        usuario_id=usuario_id,
        data=datetime.date(2026, 6, dia),
        descricao=f"desc-{id}",
        categoria="COMPRAS",
        valor=Decimal(valor),
        parcela_numero=1,
        parcela_total=1,
        tipo="GASTO",
        grupo_parcela_id=f"grupo-{id}",
        status="PENDENTE",
        forma_pagamento="PIX",
        responsavel="Jhonatas",
        detalhes=None,
    )


def _admin_token():
    return UsuarioToken(usuario_id=5, role="ADMIN", email="admin@exemplo.com")


def _construir_app():
    from backend.controllers import admin as admin_controller

    app = FastAPI()
    instalar_handlers(app)
    app.state.sessionmaker = SimpleNamespace()
    app.include_router(admin_controller.router)
    return app


def cliente_admin(usuario_repo=None, transacao_repo=None, autorizado=True):
    app = _construir_app()

    async def _fake_session():
        yield SimpleNamespace()

    app.dependency_overrides[get_session] = _fake_session
    app.dependency_overrides[get_session_begin] = _fake_session

    if autorizado:
        async def _admin_ok():
            return _admin_token()

        app.dependency_overrides[get_admin] = _admin_ok
    else:
        async def _admin_negado():
            raise HttpErro(403, "acesso negado")

        app.dependency_overrides[get_admin] = _admin_negado

    stack = ExitStack()
    if usuario_repo is not None:
        stack.enter_context(
            patch(
                "backend.services.admin_usuarios.UsuarioRepository",
                lambda session: usuario_repo,
            )
        )
    if transacao_repo is not None:
        stack.enter_context(
            patch(
                "backend.services.admin_transacoes.TransacaoRepository",
                lambda session: transacao_repo,
            )
        )
    return TestClient(app), stack


# ---------------------------------------------------------------------------
# Guard — USER negado / fora do allowlist
# ---------------------------------------------------------------------------


def test_user_negado_get_usuarios_403():
    client, stack = cliente_admin(autorizado=False)
    with stack:
        resposta = client.get("/admin/usuarios")
    assert resposta.status_code == 403
    assert resposta.json() == {"erro": "acesso negado"}


def test_user_negado_post_usuarios_403():
    client, stack = cliente_admin(autorizado=False)
    with stack:
        resposta = client.post("/admin/usuarios", json={"nome": "x"})
    assert resposta.status_code == 403


def test_user_negado_transacoes_cross_user_403():
    client, stack = cliente_admin(autorizado=False)
    with stack:
        resposta = client.get("/admin/usuarios/2/transacoes")
    assert resposta.status_code == 403


def test_token_admin_fora_allowlist_negado_403():
    client, stack = cliente_admin(autorizado=False)
    with stack:
        resposta = client.get("/admin/usuarios")
    assert resposta.status_code == 403
    assert resposta.json() == {"erro": "acesso negado"}


# ---------------------------------------------------------------------------
# CRUD de usuários
# ---------------------------------------------------------------------------


def test_admin_lista_usuarios_sem_senha_hash():
    usuarios = [
        make_usuario(id=1, email="a@b.com", role="USER"),
        make_usuario(id=2, nome="Bob", username="bob", email="bob@b.com"),
    ]
    repo = SimpleNamespace(listar=AsyncMock(return_value=usuarios))
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.get("/admin/usuarios")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert isinstance(corpo, list)
    assert len(corpo) == 2
    for item in corpo:
        assert "senha_hash" not in item
        for campo in ("id", "nome", "username", "email", "telefone", "role", "ativo", "criado_em"):
            assert campo in item


def test_admin_obtem_usuario_por_id_sem_senha_hash():
    usuario = make_usuario(id=3, email="c@b.com")
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=usuario))
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.get("/admin/usuarios/3")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["id"] == 3
    assert "senha_hash" not in corpo


def test_admin_usuario_inexistente_404():
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.get("/admin/usuarios/9999")
    assert resposta.status_code == 404


def test_admin_cria_usuario_201_com_hash_bcrypt():
    criado = make_usuario(id=10, nome="Carol", username="carol", email="carol@example.com")
    repo = SimpleNamespace(
        buscar_por_email=AsyncMock(return_value=None),
        criar=AsyncMock(return_value=criado),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.post(
            "/admin/usuarios",
            json={
                "nome": "Carol",
                "username": "carol",
                "email": "carol@example.com",
                "senha": "abc123",
                "role": "USER",
            },
        )

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert "senha_hash" not in corpo
    assert corpo["email"] == "carol@example.com"

    dto = repo.criar.await_args.args[0]
    assert dto.senha_hash.startswith("$2b$")
    assert verificar_senha("abc123", dto.senha_hash)


def test_admin_cria_usuario_email_duplicado_409():
    repo = SimpleNamespace(
        buscar_por_email=AsyncMock(return_value=make_usuario(id=1, email="carol@example.com")),
        criar=AsyncMock(),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.post(
            "/admin/usuarios",
            json={
                "nome": "Carol",
                "username": "carol",
                "email": "carol@example.com",
                "senha": "abc123",
            },
        )

    assert resposta.status_code == 409
    repo.criar.assert_not_awaited()


def test_admin_edita_nome_e_role():
    atual = make_usuario(id=3, nome="Antigo", role="USER")
    atualizado = make_usuario(id=3, nome="Novo", role="ADMIN")
    repo = SimpleNamespace(
        buscar_por_id=AsyncMock(return_value=atual),
        buscar_por_email=AsyncMock(return_value=None),
        atualizar=AsyncMock(return_value=atualizado),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.put("/admin/usuarios/3", json={"nome": "Novo", "role": "ADMIN"})

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["nome"] == "Novo"
    assert corpo["role"] == "ADMIN"
    assert "senha_hash" not in corpo


def test_admin_reseta_senha_gera_novo_hash():
    atual = make_usuario(id=3, senha_hash="$2b$hashantigo")
    repo = SimpleNamespace(
        buscar_por_id=AsyncMock(return_value=atual),
        buscar_por_email=AsyncMock(return_value=None),
        atualizar=AsyncMock(return_value=atual),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.put("/admin/usuarios/3", json={"senha": "nova-senha-segura"})

    assert resposta.status_code == 200
    dto = repo.atualizar.await_args.args[1]
    assert dto.senha_hash is not None
    assert dto.senha_hash.startswith("$2b$")
    assert verificar_senha("nova-senha-segura", dto.senha_hash)


def test_admin_inativa_usuario():
    atual = make_usuario(id=3, ativo=True)
    repo = SimpleNamespace(
        buscar_por_id=AsyncMock(return_value=atual),
        buscar_por_email=AsyncMock(return_value=None),
        atualizar=AsyncMock(return_value=make_usuario(id=3, ativo=False)),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.put("/admin/usuarios/3", json={"ativo": False})

    assert resposta.status_code == 200
    dto = repo.atualizar.await_args.args[1]
    assert dto.ativo is False
    assert resposta.json()["ativo"] is False


def test_admin_edita_usuario_inexistente_404():
    repo = SimpleNamespace(
        buscar_por_id=AsyncMock(return_value=None),
        atualizar=AsyncMock(),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.put("/admin/usuarios/9999", json={"nome": "Teste"})

    assert resposta.status_code == 404
    repo.atualizar.assert_not_awaited()


def test_admin_exclui_usuario_cascade():
    repo = SimpleNamespace(
        buscar_por_id=AsyncMock(return_value=make_usuario(id=2)),
        excluir=AsyncMock(return_value=None),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.delete("/admin/usuarios/2")

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    repo.excluir.assert_awaited_once_with(2)


def test_admin_exclui_usuario_inexistente_404():
    repo = SimpleNamespace(
        buscar_por_id=AsyncMock(return_value=None),
        excluir=AsyncMock(),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.delete("/admin/usuarios/9999")

    assert resposta.status_code == 404
    repo.excluir.assert_not_awaited()


def test_resposta_criacao_nunca_expoe_senha_hash():
    criado = make_usuario(id=11, email="novo@b.com")
    repo = SimpleNamespace(
        buscar_por_email=AsyncMock(return_value=None),
        criar=AsyncMock(return_value=criado),
    )
    client, stack = cliente_admin(usuario_repo=repo)
    with stack:
        resposta = client.post(
            "/admin/usuarios",
            json={
                "nome": "Novo",
                "username": "novo",
                "email": "novo@b.com",
                "senha": "x",
            },
        )

    assert "senha_hash" not in resposta.text


# ---------------------------------------------------------------------------
# CRUD de transações cross-user
# ---------------------------------------------------------------------------


def test_admin_lista_transacoes_de_outro_usuario():
    transacoes = [make_transacao(1, usuario_id=2), make_transacao(2, usuario_id=2)]
    repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_admin(transacao_repo=repo)
    with stack:
        resposta = client.get("/admin/usuarios/2/transacoes")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo) == 2
    assert {"id", "data", "valor", "categoria", "tipo"} <= set(corpo[0].keys())
    _, kwargs = repo.listar_por_periodo.await_args
    assert kwargs.get("usuario_id") == 2


def test_admin_cria_transacao_para_outro_usuario():
    repo = SimpleNamespace(criar=AsyncMock(return_value=SimpleNamespace(id=99)))
    client, stack = cliente_admin(transacao_repo=repo)
    with stack:
        resposta = client.post(
            "/admin/usuarios/2/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 201
    dto = repo.criar.await_args.args[0]
    assert dto.usuario_id == 2


def test_admin_obtem_transacao_qualquer_dono():
    transacao = make_transacao(50, usuario_id=2)
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=transacao))
    client, stack = cliente_admin(transacao_repo=repo)
    with stack:
        resposta = client.get("/admin/transacoes/50")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == 50
    _, kwargs = repo.buscar_por_id.await_args
    assert kwargs.get("usuario_id") is None


def test_admin_obtem_transacao_inexistente_404():
    repo = SimpleNamespace(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente_admin(transacao_repo=repo)
    with stack:
        resposta = client.get("/admin/transacoes/9999")
    assert resposta.status_code == 404


def test_admin_edita_transacao_qualquer_dono():
    transacao = make_transacao(50, usuario_id=2)
    repo = SimpleNamespace(
        buscar_por_id=AsyncMock(return_value=transacao),
        atualizar=AsyncMock(return_value=transacao),
    )
    client, stack = cliente_admin(transacao_repo=repo)
    with stack:
        resposta = client.put("/admin/transacoes/50", json={"valor": "99.00"})

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    _, kwargs = repo.atualizar.await_args
    assert kwargs.get("usuario_id") is None


def test_admin_exclui_transacao_qualquer_dono():
    transacao = make_transacao(50, usuario_id=2)
    repo = SimpleNamespace(
        buscar_por_id=AsyncMock(return_value=transacao),
        excluir=AsyncMock(return_value=None),
    )
    client, stack = cliente_admin(transacao_repo=repo)
    with stack:
        resposta = client.delete("/admin/transacoes/50")

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    repo.excluir.assert_awaited_once_with(50, usuario_id=None)
