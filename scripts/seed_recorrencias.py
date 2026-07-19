"""Seed de recorrencias a partir dos gastos fixos avulsos existentes.

Uso:
    uv run python scripts/seed_recorrencias.py [--dry-run]

Para cada usuario, olha as transacoes ``categoria=GASTOS_FIXOS`` e
``parcela_total=1`` do MES MAIS RECENTE em que existam, deduplica por
``lower(descricao)`` e cria uma ``Recorrencia`` (ativo=true, tipo=GASTO,
categoria=GASTOS_FIXOS, valor, descricao) para cada uma.

Idempotente: nao cria uma recorrencia se ja houver outra com a mesma
``lower(descricao)`` para aquele usuario.

A logica de selecao vive em funcoes puras (``gastos_fixos_do_mes_recente``,
``novas_recorrencias``) testaveis sem banco; apenas ``main`` abre sessao real.
"""

import argparse
import asyncio
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable, Sequence

CATEGORIA = "GASTOS_FIXOS"


def _como_str(campo) -> str:
    return getattr(campo, "value", campo)


@dataclass
class RecorrenciaSemente:
    usuario_id: int
    descricao: str
    valor: Decimal


def gastos_fixos_do_mes_recente(transacoes: Iterable) -> list:
    """Filtra GASTOS_FIXOS avulsos e devolve apenas os do mes mais recente."""
    fixos = [
        t
        for t in transacoes
        if _como_str(t.categoria) == CATEGORIA and t.parcela_total == 1
    ]
    if not fixos:
        return []
    mes_recente = max((t.data.year, t.data.month) for t in fixos)
    return [t for t in fixos if (t.data.year, t.data.month) == mes_recente]


def novas_recorrencias(
    usuario_id: int, transacoes: Sequence, descricoes_existentes: set[str]
) -> list[RecorrenciaSemente]:
    """Deduplica por lower(descricao) e ignora as ja existentes."""
    vistas = set(descricoes_existentes)
    resultado: list[RecorrenciaSemente] = []
    for t in gastos_fixos_do_mes_recente(transacoes):
        chave = (t.descricao or "").strip().lower()
        if not chave or chave in vistas:
            continue
        vistas.add(chave)
        resultado.append(
            RecorrenciaSemente(
                usuario_id=usuario_id,
                descricao=t.descricao,
                valor=t.valor,
            )
        )
    return resultado


async def executar_seed(session, dry_run: bool) -> list[RecorrenciaSemente]:
    from backend.models.enums import CategoriaEnum, TipoEnum
    from backend.repositories.recorrencia_repository import RecorrenciaRepository
    from backend.repositories.transacao_repository import TransacaoRepository
    from backend.repositories.usuario_repository import UsuarioRepository

    inicio = date(2000, 1, 1)
    fim = date(2099, 12, 31)

    usuario_repo = UsuarioRepository(session)
    trans_repo = TransacaoRepository(session)
    rec_repo = RecorrenciaRepository(session)

    criadas: list[RecorrenciaSemente] = []
    for usuario in await usuario_repo.listar():
        transacoes = await trans_repo.listar_por_periodo(
            inicio, fim, usuario_id=usuario.id
        )
        existentes = await rec_repo.listar(usuario.id)
        descricoes_existentes = {
            (r.descricao or "").strip().lower() for r in existentes
        }
        sementes = novas_recorrencias(
            usuario.id, transacoes, descricoes_existentes
        )
        criadas.extend(sementes)
        if not dry_run:
            for semente in sementes:
                await rec_repo.criar(
                    usuario_id=semente.usuario_id,
                    descricao=semente.descricao,
                    tipo=TipoEnum.GASTO,
                    categoria=CategoriaEnum.GASTOS_FIXOS,
                    valor=semente.valor,
                    ativo=True,
                )
    return criadas


def formatar_relatorio(criadas: Sequence[RecorrenciaSemente], dry_run: bool) -> str:
    linhas = ["=== Seed de recorrencias ==="]
    if dry_run:
        linhas.append("(dry-run: nada foi gravado)")
    linhas.append(f"Recorrencias criadas: {len(criadas)}")
    for c in criadas:
        linhas.append(
            f"  [usuario {c.usuario_id}] {c.descricao} — {c.valor}"
        )
    return "\n".join(linhas)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria recorrencias a partir dos gastos fixos avulsos existentes."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas imprime o que seria feito, sem gravar no banco.",
    )
    args = parser.parse_args()

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from agent.config import settings

    _engine = create_async_engine(settings.DATABASE_URL)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _session_factory() as session:
        async with session.begin():
            criadas = await executar_seed(session, dry_run=args.dry_run)

    print(formatar_relatorio(criadas, dry_run=args.dry_run))


if __name__ == "__main__":
    asyncio.run(main())
