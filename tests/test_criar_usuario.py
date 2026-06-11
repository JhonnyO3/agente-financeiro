from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.auth.hashing import verificar_senha
from backend.models.enums import RoleEnum


def _args(**kwargs) -> Namespace:
    defaults = dict(
        nome="Alice",
        username="alice",
        email="alice@example.com",
        senha="abc123",
        telefone=None,
        role="USER",
    )
    defaults.update(kwargs)
    return Namespace(**defaults)


def _repo_sem_usuario() -> MagicMock:
    repo = MagicMock()
    repo.buscar_por_email = AsyncMock(return_value=None)
    repo.criar = AsyncMock(
        return_value=SimpleNamespace(id=1, email="alice@example.com", role=RoleEnum.USER)
    )
    repo.atualizar = AsyncMock()
    return repo


def _repo_com_usuario(usuario) -> MagicMock:
    repo = MagicMock()
    repo.buscar_por_email = AsyncMock(return_value=usuario)
    repo.criar = AsyncMock()
    repo.atualizar = AsyncMock(return_value=usuario)
    return repo


# ---------------------------------------------------------------------------
# parse_args — validação de obrigatórios
# ---------------------------------------------------------------------------


def test_parse_args_falha_quando_email_ausente():
    from scripts.criar_usuario import parse_args

    with pytest.raises(SystemExit) as exc:
        parse_args(["--nome", "Alice", "--username", "alice", "--senha", "abc123"])
    assert exc.value.code != 0


def test_parse_args_falha_quando_senha_ausente():
    from scripts.criar_usuario import parse_args

    with pytest.raises(SystemExit) as exc:
        parse_args(
            ["--nome", "Alice", "--username", "alice", "--email", "alice@example.com"]
        )
    assert exc.value.code != 0


def test_parse_args_role_default_user():
    from scripts.criar_usuario import parse_args

    args = parse_args(
        [
            "--nome",
            "Alice",
            "--username",
            "alice",
            "--email",
            "alice@example.com",
            "--senha",
            "abc123",
        ]
    )
    assert args.role == "USER"
    assert args.telefone is None


def test_parse_args_aceita_role_admin_e_telefone():
    from scripts.criar_usuario import parse_args

    args = parse_args(
        [
            "--nome",
            "Jhonatas",
            "--username",
            "jhonatas",
            "--email",
            "jhonatas2004@gmail.com",
            "--senha",
            "x",
            "--role",
            "ADMIN",
            "--telefone",
            "11999990001",
        ]
    )
    assert args.role == "ADMIN"
    assert args.telefone == "11999990001"


def test_parse_args_rejeita_role_invalida():
    from scripts.criar_usuario import parse_args

    with pytest.raises(SystemExit) as exc:
        parse_args(
            [
                "--nome",
                "A",
                "--username",
                "a",
                "--email",
                "a@example.com",
                "--senha",
                "x",
                "--role",
                "ROOT",
            ]
        )
    assert exc.value.code != 0


# ---------------------------------------------------------------------------
# executar — criação
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_executar_cria_usuario_role_user():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    await executar(repo, _args())

    repo.criar.assert_awaited_once()
    dto = repo.criar.call_args[0][0]
    assert dto.email == "alice@example.com"
    assert dto.role == RoleEnum.USER
    repo.atualizar.assert_not_awaited()


@pytest.mark.asyncio
async def test_executar_cria_usuario_role_admin():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    await executar(repo, _args(role="ADMIN", email="admin@example.com"))

    dto = repo.criar.call_args[0][0]
    assert dto.role == RoleEnum.ADMIN


@pytest.mark.asyncio
async def test_executar_cria_admin_padrao_jhonatas():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    await executar(
        repo,
        _args(
            nome="Jhonatas",
            username="jhonatas",
            email="jhonatas2004@gmail.com",
            senha="senha-forte",
            role="ADMIN",
        ),
    )

    dto = repo.criar.call_args[0][0]
    assert dto.email == "jhonatas2004@gmail.com"
    assert dto.role == RoleEnum.ADMIN


@pytest.mark.asyncio
async def test_executar_telefone_opcional_persistido():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    await executar(repo, _args(telefone="11999990001"))

    dto = repo.criar.call_args[0][0]
    assert dto.telefone == "11999990001"


@pytest.mark.asyncio
async def test_executar_telefone_ausente_fica_none():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    await executar(repo, _args())

    dto = repo.criar.call_args[0][0]
    assert dto.telefone is None


# ---------------------------------------------------------------------------
# executar — senha vira hash bcrypt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_senha_gravada_e_hash_bcrypt():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    await executar(repo, _args(senha="minha-senha-segura"))

    dto = repo.criar.call_args[0][0]
    assert dto.senha_hash.startswith("$2b$")
    assert dto.senha_hash != "minha-senha-segura"


@pytest.mark.asyncio
async def test_senha_hash_verificavel_e_nao_recuperavel():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    await executar(repo, _args(senha="segredo-123"))

    dto = repo.criar.call_args[0][0]
    assert "segredo-123" not in dto.senha_hash
    assert verificar_senha("segredo-123", dto.senha_hash)
    assert not verificar_senha("outra-senha", dto.senha_hash)


# ---------------------------------------------------------------------------
# executar — idempotência por email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_executar_email_existente_atualiza_hash():
    from scripts.criar_usuario import executar

    usuario = SimpleNamespace(
        id=42, email="alice@example.com", role=RoleEnum.USER, senha_hash="hash-antigo"
    )
    repo = _repo_com_usuario(usuario)

    await executar(repo, _args(senha="nova-senha"))

    repo.criar.assert_not_awaited()
    repo.atualizar.assert_awaited_once()
    chamada_id = repo.atualizar.call_args[0][0]
    assert chamada_id == 42
    update = repo.atualizar.call_args[0][1]
    assert verificar_senha("nova-senha", update.senha_hash)


@pytest.mark.asyncio
async def test_executar_email_existente_mensagem_clara_atualizado():
    from scripts.criar_usuario import executar

    usuario = SimpleNamespace(
        id=42, email="alice@example.com", role=RoleEnum.USER, senha_hash="hash-antigo"
    )
    repo = _repo_com_usuario(usuario)

    mensagem = await executar(repo, _args(senha="nova-senha"))

    assert "atualizado" in mensagem.lower()
    assert "alice@example.com" in mensagem


@pytest.mark.asyncio
async def test_executar_email_novo_mensagem_clara_criado():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    mensagem = await executar(repo, _args())

    assert "criado" in mensagem.lower()
    assert "alice@example.com" in mensagem


# ---------------------------------------------------------------------------
# executar — a saída nunca vaza a senha
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_saida_nao_contem_senha_ao_criar():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    mensagem = await executar(repo, _args(senha="segredo-especial"))

    assert "segredo-especial" not in mensagem


@pytest.mark.asyncio
async def test_saida_nao_contem_senha_ao_atualizar():
    from scripts.criar_usuario import executar

    usuario = SimpleNamespace(
        id=42, email="alice@example.com", role=RoleEnum.USER, senha_hash="hash-antigo"
    )
    repo = _repo_com_usuario(usuario)

    mensagem = await executar(repo, _args(senha="segredo-especial"))

    assert "segredo-especial" not in mensagem


@pytest.mark.asyncio
async def test_saida_inclui_email_e_role():
    from scripts.criar_usuario import executar

    repo = _repo_sem_usuario()
    mensagem = await executar(repo, _args(role="USER"))

    assert "alice@example.com" in mensagem
    assert "USER" in mensagem
