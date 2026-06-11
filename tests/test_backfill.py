"""Testes do script de backfill de parcelas (T10).

A lógica de decisão fica em funções puras (`analisar_grupo`, `agrupar_por_grupo`,
`formatar_relatorio`); o orquestrador `executar_backfill` é testado com repository
mockado. O `main` (sessão real) não é executado aqui.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

HOJE = date(2026, 6, 10)
GRUPO_ID = "11111111-1111-1111-1111-111111111111"


def _make_transacao(
    id=1,
    tipo="GASTO",
    valor=Decimal("100.00"),
    descricao="notebook",
    categoria="PARCELAMENTOS",
    data=date(2026, 6, 10),
    parcela_numero=1,
    parcela_total=4,
    grupo_parcela_id=GRUPO_ID,
    embedding=None,
    status="PENDENTE",
    forma_pagamento="CARTAO",
    responsavel="Jhonatas",
    detalhes=None,
):
    t = MagicMock()
    t.id = id
    t.tipo = tipo
    t.valor = valor
    t.descricao = descricao
    t.categoria = categoria
    t.data = data
    t.parcela_numero = parcela_numero
    t.parcela_total = parcela_total
    t.grupo_parcela_id = grupo_parcela_id
    t.embedding = embedding if embedding is not None else [0.1] * 1536
    t.status = status
    t.forma_pagamento = forma_pagamento
    t.responsavel = responsavel
    t.detalhes = detalhes
    return t


# ---------------------------------------------------------------------------
# analisar_grupo — função pura
# ---------------------------------------------------------------------------


def test_analisar_grupo_incompleto_cria_faltantes_com_datas_e_status():
    from backend.models.enums import StatusEnum
    from scripts.backfill_parcelas import analisar_grupo

    existente = _make_transacao(parcela_numero=2, data=date(2026, 6, 10), parcela_total=4)

    resultado = analisar_grupo([existente], hoje=HOJE)

    assert resultado.motivo_ambiguidade is None
    assert len(resultado.faltantes) == 3

    por_numero = {f.parcela_numero: f for f in resultado.faltantes}
    assert sorted(por_numero) == [1, 3, 4]

    assert por_numero[1].data == date(2026, 5, 10)
    assert por_numero[1].status == StatusEnum.PAGO
    assert por_numero[3].data == date(2026, 7, 10)
    assert por_numero[3].status == StatusEnum.PENDENTE
    assert por_numero[4].data == date(2026, 8, 10)
    assert por_numero[4].status == StatusEnum.PENDENTE


def test_analisar_grupo_copia_campos_do_grupo():
    from scripts.backfill_parcelas import analisar_grupo

    embedding = [0.5] * 1536
    existente = _make_transacao(
        parcela_numero=2,
        data=date(2026, 6, 10),
        parcela_total=4,
        valor=Decimal("250.00"),
        descricao="celular",
        categoria="PARCELAMENTOS",
        tipo="GASTO",
        embedding=embedding,
        forma_pagamento="CARTAO",
        responsavel="Jhonatas",
        detalhes="loja X",
    )

    resultado = analisar_grupo([existente], hoje=HOJE)

    for faltante in resultado.faltantes:
        assert faltante.valor == Decimal("250.00")
        assert faltante.descricao == "celular"
        assert faltante.categoria == "PARCELAMENTOS"
        assert faltante.tipo == "GASTO"
        assert faltante.embedding == embedding
        assert faltante.forma_pagamento == "CARTAO"
        assert faltante.responsavel == "Jhonatas"
        assert faltante.detalhes == "loja X"
        assert str(faltante.grupo_parcela_id) == GRUPO_ID
        assert faltante.parcela_total == 4


def test_analisar_grupo_completo_nao_cria_nada():
    from scripts.backfill_parcelas import analisar_grupo

    grupo = [
        _make_transacao(id=i, parcela_numero=i, data=date(2026, 5 + i, 10), parcela_total=3)
        for i in (1, 2, 3)
    ]

    resultado = analisar_grupo(grupo, hoje=HOJE)

    assert resultado.faltantes == []
    assert resultado.motivo_ambiguidade is None


def test_analisar_grupo_valores_divergentes_e_ambiguo():
    from scripts.backfill_parcelas import analisar_grupo

    grupo = [
        _make_transacao(id=1, parcela_numero=1, valor=Decimal("100.00")),
        _make_transacao(id=2, parcela_numero=2, valor=Decimal("999.00")),
    ]

    resultado = analisar_grupo(grupo, hoje=HOJE)

    assert resultado.faltantes == []
    assert resultado.motivo_ambiguidade is not None
    assert "valor" in resultado.motivo_ambiguidade.lower()


def test_analisar_grupo_descricoes_divergentes_e_ambiguo():
    from scripts.backfill_parcelas import analisar_grupo

    grupo = [
        _make_transacao(id=1, parcela_numero=1, descricao="notebook"),
        _make_transacao(id=2, parcela_numero=2, descricao="geladeira"),
    ]

    resultado = analisar_grupo(grupo, hoje=HOJE)

    assert resultado.faltantes == []
    assert "descricao" in (resultado.motivo_ambiguidade or "").lower()


def test_analisar_grupo_parcela_total_divergente_e_ambiguo():
    from scripts.backfill_parcelas import analisar_grupo

    grupo = [
        _make_transacao(id=1, parcela_numero=1, parcela_total=4),
        _make_transacao(id=2, parcela_numero=2, parcela_total=6),
    ]

    resultado = analisar_grupo(grupo, hoje=HOJE)

    assert resultado.faltantes == []
    assert "parcela_total" in (resultado.motivo_ambiguidade or "").lower()


def test_analisar_grupo_parcela_numero_duplicado_e_ambiguo():
    from scripts.backfill_parcelas import analisar_grupo

    grupo = [
        _make_transacao(id=1, parcela_numero=2),
        _make_transacao(id=2, parcela_numero=2),
    ]

    resultado = analisar_grupo(grupo, hoje=HOJE)

    assert resultado.faltantes == []
    assert "duplicad" in (resultado.motivo_ambiguidade or "").lower()


def test_analisar_grupo_parcela_numero_maior_que_total_e_ambiguo():
    from scripts.backfill_parcelas import analisar_grupo

    grupo = [_make_transacao(id=1, parcela_numero=5, parcela_total=4)]

    resultado = analisar_grupo(grupo, hoje=HOJE)

    assert resultado.faltantes == []
    assert resultado.motivo_ambiguidade is not None


# ---------------------------------------------------------------------------
# agrupar_por_grupo — função pura
# ---------------------------------------------------------------------------


def test_agrupar_por_grupo_filtra_e_agrupa():
    from scripts.backfill_parcelas import agrupar_por_grupo

    outro_grupo = "22222222-2222-2222-2222-222222222222"
    avulsa = "33333333-3333-3333-3333-333333333333"
    transacoes = [
        _make_transacao(id=1, parcela_numero=1, grupo_parcela_id=GRUPO_ID),
        _make_transacao(id=2, parcela_numero=2, grupo_parcela_id=GRUPO_ID),
        _make_transacao(id=3, parcela_numero=1, parcela_total=2, grupo_parcela_id=outro_grupo),
        _make_transacao(id=4, parcela_numero=1, parcela_total=1, grupo_parcela_id=avulsa),
    ]

    grupos = agrupar_por_grupo(transacoes)

    assert set(grupos) == {GRUPO_ID, outro_grupo}
    assert [t.id for t in grupos[GRUPO_ID]] == [1, 2]
    assert [t.id for t in grupos[outro_grupo]] == [3]


# ---------------------------------------------------------------------------
# executar_backfill — repository mockado
# ---------------------------------------------------------------------------


def _make_repository(transacoes):
    repository = MagicMock()
    repository.listar_por_periodo = AsyncMock(return_value=transacoes)
    repository.listar_por_periodo_com_embedding = AsyncMock(return_value=transacoes)
    repository.criar_lote = AsyncMock(return_value=[])
    return repository


@pytest.mark.asyncio
async def test_executar_backfill_cria_faltantes_de_grupo_incompleto():
    from scripts.backfill_parcelas import executar_backfill

    existente = _make_transacao(parcela_numero=2, data=date(2026, 6, 10), parcela_total=4)
    repository = _make_repository([existente])

    resultados = await executar_backfill(repository, dry_run=False, hoje=HOJE)

    repository.criar_lote.assert_awaited_once()
    criadas = repository.criar_lote.await_args.args[0]
    assert sorted(c.parcela_numero for c in criadas) == [1, 3, 4]
    assert len(resultados) == 1
    assert len(resultados[0].faltantes) == 3


@pytest.mark.asyncio
async def test_executar_backfill_idempotente_grupo_completo():
    from scripts.backfill_parcelas import executar_backfill

    grupo = [
        _make_transacao(id=i, parcela_numero=i, data=date(2026, 5 + i, 10), parcela_total=3)
        for i in (1, 2, 3)
    ]
    repository = _make_repository(grupo)

    resultados = await executar_backfill(repository, dry_run=False, hoje=HOJE)

    repository.criar_lote.assert_not_awaited()
    assert resultados[0].faltantes == []


@pytest.mark.asyncio
async def test_executar_backfill_dry_run_nao_chama_criar_lote():
    from scripts.backfill_parcelas import executar_backfill

    existente = _make_transacao(parcela_numero=2, data=date(2026, 6, 10), parcela_total=4)
    repository = _make_repository([existente])

    resultados = await executar_backfill(repository, dry_run=True, hoje=HOJE)

    repository.criar_lote.assert_not_awaited()
    assert len(resultados[0].faltantes) == 3


@pytest.mark.asyncio
async def test_executar_backfill_grupo_ambiguo_fica_intacto():
    from scripts.backfill_parcelas import executar_backfill

    grupo = [
        _make_transacao(id=1, parcela_numero=1, valor=Decimal("100.00")),
        _make_transacao(id=2, parcela_numero=2, valor=Decimal("999.00")),
    ]
    repository = _make_repository(grupo)

    resultados = await executar_backfill(repository, dry_run=False, hoje=HOJE)

    repository.criar_lote.assert_not_awaited()
    assert resultados[0].motivo_ambiguidade is not None


# ---------------------------------------------------------------------------
# formatar_relatorio — função pura
# ---------------------------------------------------------------------------


def test_formatar_relatorio_lista_completados_criadas_e_pulados():
    from scripts.backfill_parcelas import analisar_grupo, formatar_relatorio

    incompleto = analisar_grupo(
        [_make_transacao(parcela_numero=2, data=date(2026, 6, 10), parcela_total=4)],
        hoje=HOJE,
    )
    ambiguo = analisar_grupo(
        [
            _make_transacao(
                id=1,
                parcela_numero=1,
                valor=Decimal("100.00"),
                grupo_parcela_id="22222222-2222-2222-2222-222222222222",
            ),
            _make_transacao(
                id=2,
                parcela_numero=2,
                valor=Decimal("999.00"),
                grupo_parcela_id="22222222-2222-2222-2222-222222222222",
            ),
        ],
        hoje=HOJE,
    )
    completo = analisar_grupo(
        [
            _make_transacao(
                id=i,
                parcela_numero=i,
                parcela_total=2,
                grupo_parcela_id="33333333-3333-3333-3333-333333333333",
            )
            for i in (1, 2)
        ],
        hoje=HOJE,
    )

    relatorio = formatar_relatorio([incompleto, ambiguo, completo], dry_run=False)

    assert "Grupos completados: 1" in relatorio
    assert "Parcelas criadas: 3" in relatorio
    assert "Grupos pulados: 1" in relatorio
    assert ambiguo.motivo_ambiguidade in relatorio


def test_formatar_relatorio_dry_run_indica_simulacao():
    from scripts.backfill_parcelas import analisar_grupo, formatar_relatorio

    incompleto = analisar_grupo(
        [_make_transacao(parcela_numero=2, data=date(2026, 6, 10), parcela_total=4)],
        hoje=HOJE,
    )

    relatorio = formatar_relatorio([incompleto], dry_run=True)

    assert "dry-run" in relatorio.lower()
