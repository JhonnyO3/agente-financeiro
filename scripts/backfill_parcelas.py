"""Backfill de parcelas faltantes em grupos de parcelamento.

Uso:
    uv run python scripts/backfill_parcelas.py [--dry-run]

Percorre as transações com ``parcela_total > 1``, agrupa por
``grupo_parcela_id`` e, para cada grupo incompleto e CONSISTENTE, cria as
parcelas faltantes (data derivada via ``adicionar_meses``, status via
``status_por_data``, demais campos copiados do grupo). Grupos ambíguos são
pulados e listados no relatório com o motivo.

A lógica de decisão fica em funções puras (``agrupar_por_grupo``,
``analisar_grupo``, ``formatar_relatorio``) testáveis sem banco; apenas
``main`` abre sessão real via ``app.repositories.database``.
"""

import argparse
import asyncio
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Sequence
from uuid import UUID

from app.repositories.dtos import TransacaoCreate
from app.services.parcelas import adicionar_meses, status_por_data

PERIODO_INICIO = date(2000, 1, 1)
PERIODO_FIM = date(2035, 12, 31)


@dataclass
class ResultadoAnalise:
    """Resultado da análise de um grupo de parcelas."""

    grupo_parcela_id: str
    parcela_total: int
    existentes: int
    faltantes: list[TransacaoCreate] = field(default_factory=list)
    motivo_ambiguidade: str | None = None

    @property
    def ambiguo(self) -> bool:
        return self.motivo_ambiguidade is not None

    @property
    def completado(self) -> bool:
        return not self.ambiguo and len(self.faltantes) > 0


def agrupar_por_grupo(transacoes: Iterable) -> dict[str, list]:
    """Filtra transações com parcela_total > 1 e agrupa por grupo_parcela_id."""
    grupos: dict[str, list] = {}
    for t in transacoes:
        if t.parcela_total is None or t.parcela_total <= 1:
            continue
        grupos.setdefault(str(t.grupo_parcela_id), []).append(t)
    return grupos


def _motivo_ambiguidade(transacoes: Sequence) -> str | None:
    """Devolve o motivo de ambiguidade do grupo, ou None se consistente."""
    if len({t.parcela_total for t in transacoes}) > 1:
        return "parcela_total divergente entre as parcelas"
    if len({t.valor for t in transacoes}) > 1:
        return "valores divergentes entre as parcelas"
    if len({t.descricao for t in transacoes}) > 1:
        return "descricao divergente entre as parcelas"

    numeros = [t.parcela_numero for t in transacoes]
    if len(numeros) != len(set(numeros)):
        return "parcela_numero duplicado no grupo"

    parcela_total = transacoes[0].parcela_total
    if any(n < 1 or n > parcela_total for n in numeros):
        return "parcela_numero fora do intervalo 1..parcela_total"

    return None


def analisar_grupo(transacoes: Sequence, hoje: date | None = None) -> ResultadoAnalise:
    """Analisa um grupo: devolve as parcelas faltantes a criar OU o motivo
    pelo qual o grupo é ambíguo e deve ser pulado. Função pura (sem DB)."""
    grupo_id = str(transacoes[0].grupo_parcela_id)

    motivo = _motivo_ambiguidade(transacoes)
    if motivo is not None:
        return ResultadoAnalise(
            grupo_parcela_id=grupo_id,
            parcela_total=max(t.parcela_total for t in transacoes),
            existentes=len(transacoes),
            motivo_ambiguidade=motivo,
        )

    referencia = min(transacoes, key=lambda t: t.parcela_numero)
    parcela_total = referencia.parcela_total
    numeros_existentes = {t.parcela_numero for t in transacoes}

    faltantes = [
        TransacaoCreate(
            tipo=referencia.tipo,
            valor=referencia.valor,
            descricao=referencia.descricao,
            categoria=referencia.categoria,
            data=(data_parcela := adicionar_meses(
                referencia.data, numero - referencia.parcela_numero
            )),
            parcela_numero=numero,
            parcela_total=parcela_total,
            grupo_parcela_id=UUID(grupo_id),
            embedding=referencia.embedding,
            status=status_por_data(data_parcela, hoje=hoje),
            forma_pagamento=referencia.forma_pagamento,
            responsavel=referencia.responsavel,
            detalhes=referencia.detalhes,
        )
        for numero in range(1, parcela_total + 1)
        if numero not in numeros_existentes
    ]

    return ResultadoAnalise(
        grupo_parcela_id=grupo_id,
        parcela_total=parcela_total,
        existentes=len(transacoes),
        faltantes=faltantes,
    )


async def executar_backfill(
    repository, dry_run: bool, hoje: date | None = None
) -> list[ResultadoAnalise]:
    """Busca os grupos, analisa cada um e (fora do dry-run) cria as faltantes."""
    transacoes = await repository.listar_por_periodo_com_embedding(PERIODO_INICIO, PERIODO_FIM)
    grupos = agrupar_por_grupo(transacoes)

    resultados = [analisar_grupo(grupo, hoje=hoje) for grupo in grupos.values()]

    if not dry_run:
        for resultado in resultados:
            if resultado.faltantes:
                await repository.criar_lote(resultado.faltantes)

    return resultados


def formatar_relatorio(resultados: Sequence[ResultadoAnalise], dry_run: bool) -> str:
    """Monta o relatório final para o stdout."""
    completados = [r for r in resultados if r.completado]
    pulados = [r for r in resultados if r.ambiguo]
    parcelas_criadas = sum(len(r.faltantes) for r in completados)

    linhas = ["=== Backfill de parcelas ==="]
    if dry_run:
        linhas.append("(dry-run: nada foi gravado)")

    linhas.append(f"Grupos analisados: {len(resultados)}")
    linhas.append(f"Grupos completados: {len(completados)}")
    linhas.append(f"Parcelas criadas: {parcelas_criadas}")
    linhas.append(f"Grupos pulados: {len(pulados)}")

    for r in completados:
        numeros = ", ".join(str(f.parcela_numero) for f in r.faltantes)
        linhas.append(
            f"  [completado] grupo {r.grupo_parcela_id}: "
            f"{r.existentes}/{r.parcela_total} existentes, criadas parcelas {numeros}"
        )
    for r in pulados:
        linhas.append(
            f"  [pulado] grupo {r.grupo_parcela_id}: {r.motivo_ambiguidade}"
        )

    return "\n".join(linhas)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cria parcelas faltantes em grupos de parcelamento incompletos."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apenas imprime o que seria feito, sem gravar no banco.",
    )
    args = parser.parse_args()

    # Imports tardios: exigem settings (.env) e conexão com o banco.
    from app.repositories.database import AsyncSessionLocal
    from app.repositories.transacao_repository import TransacaoRepository

    async with AsyncSessionLocal() as session:
        async with session.begin():
            repository = TransacaoRepository(session)
            resultados = await executar_backfill(repository, dry_run=args.dry_run)

    print(formatar_relatorio(resultados, dry_run=args.dry_run))


if __name__ == "__main__":
    asyncio.run(main())
