"""Cria ou atualiza um usuário com senha bcrypt (idempotente por email).

Uso:
    uv run python scripts/criar_usuario.py \
        --nome Alice --username alice --email alice@example.com --senha abc123 \
        [--telefone 11999990001] [--role USER|ADMIN]

A decisão criar-vs-atualizar é idempotente por email: se já existe um usuário
com o email informado, seu ``senha_hash`` (e demais dados fornecidos) é
atualizado; caso contrário um novo usuário é criado. A senha em texto puro
nunca é ecoada na saída e a senha gravada é sempre um hash bcrypt one-way.

A lógica fica em ``executar(repo, args)`` (testável sem banco); apenas ``main``
abre a sessão real via ``backend.db``.
"""

import argparse
import asyncio
from argparse import Namespace

from backend.auth.hashing import hash_senha
from backend.models.enums import RoleEnum
from backend.repositories.dtos import UsuarioCreate, UsuarioUpdate


def parse_args(argv: list[str] | None = None) -> Namespace:
    parser = argparse.ArgumentParser(
        description="Cria ou atualiza um usuário com senha bcrypt (idempotente por email)."
    )
    parser.add_argument("--nome", required=True, help="Nome do usuário.")
    parser.add_argument("--username", required=True, help="Username do usuário.")
    parser.add_argument("--email", required=True, help="Email (identificador de login).")
    parser.add_argument("--senha", required=True, help="Senha em texto puro (vira hash bcrypt).")
    parser.add_argument("--telefone", default=None, help="Telefone (opcional, único quando preenchido).")
    parser.add_argument(
        "--role",
        choices=[RoleEnum.USER.value, RoleEnum.ADMIN.value],
        default=RoleEnum.USER.value,
        help="Papel do usuário (default USER).",
    )
    return parser.parse_args(argv)


async def executar(repo, args: Namespace) -> str:
    senha_hash = hash_senha(args.senha)
    role = RoleEnum(args.role)

    existente = await repo.buscar_por_email(args.email)

    if existente is not None:
        await repo.atualizar(
            existente.id,
            UsuarioUpdate(
                nome=args.nome,
                username=args.username,
                senha_hash=senha_hash,
                telefone=args.telefone,
                role=role,
            ),
        )
        return (
            f"Usuário já existia e foi atualizado: "
            f"email={args.email}, role={role.value}."
        )

    await repo.criar(
        UsuarioCreate(
            nome=args.nome,
            username=args.username,
            email=args.email,
            senha_hash=senha_hash,
            telefone=args.telefone,
            role=role,
        )
    )
    return (
        f"Usuário criado: nome={args.nome}, email={args.email}, role={role.value}."
    )


async def main() -> None:
    args = parse_args()

    from backend.config import settings
    from backend.db import criar_engine, criar_sessionmaker
    from backend.repositories.usuario_repository import UsuarioRepository

    engine = criar_engine(settings.DATABASE_URL)
    sessionmaker = criar_sessionmaker(engine)

    async with sessionmaker() as session:
        async with session.begin():
            repo = UsuarioRepository(session)
            mensagem = await executar(repo, args)

    await engine.dispose()
    print(mensagem)


if __name__ == "__main__":
    asyncio.run(main())
