"""
Testes vermelhos (TDD) — Task 10: ToolExcluir
Cenários espelhados de: specs/melhorias-agente/scenarios/10-tools-atualizar-excluir.feature

ESTADO ESPERADO: vermelho (red) — agent/tools/excluir.py ainda não existe.
"""

import os
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_API_KEY", "evo-test")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "+5511999999999")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "admin@exemplo.com")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Teste")
os.environ.setdefault("WEBHOOK_APIKEY", "webhook-secret")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ADMIN_EMAILS", "admin@exemplo.com")

import pytest

from backend.models.enums import CategoriaEnum, FormaPagamentoEnum, StatusEnum, TipoEnum
from backend.models.transacao import Transacao
from agent.domain.intencao import ParamsExcluir
from agent.domain.resultado import ResultadoTool
from agent.services.relogio import Relogio

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

_UTC_FIXO = datetime(2026, 6, 12, 15, 0, 0, tzinfo=timezone.utc)
_RELOGIO = Relogio("America/Sao_Paulo", _fixed=_UTC_FIXO)

GRUPO_G1 = str(uuid4())


def _make_transacao(
    id: int = 1,
    descricao: str = "Flores Natasha",
    valor: Decimal = Decimal("140.00"),
    data: date = date(2026, 6, 11),
    categoria: CategoriaEnum = CategoriaEnum.COMPRAS,
    forma_pagamento: FormaPagamentoEnum = FormaPagamentoEnum.PIX,
    status: StatusEnum = StatusEnum.PAGO,
    parcela_numero: int = 1,
    parcela_total: int = 1,
    grupo_parcela_id: str | None = None,
    usuario_id: int = 1,
) -> MagicMock:
    t = MagicMock(spec=Transacao)
    t.id = id
    t.descricao = descricao
    t.valor = valor
    t.data = data
    t.categoria = categoria
    t.forma_pagamento = forma_pagamento
    t.status = status
    t.parcela_numero = parcela_numero
    t.parcela_total = parcela_total
    t.grupo_parcela_id = grupo_parcela_id or str(uuid4())
    t.usuario_id = usuario_id
    t.tipo = TipoEnum.GASTO
    t.responsavel = "Jhonatas"
    t.detalhes = None
    return t


def _rag_match(transacao: MagicMock) -> MagicMock:
    from agent.services.rag import Faixa, ResultadoBusca  # type: ignore[import]

    busca = MagicMock()
    busca.buscar = AsyncMock(
        return_value=ResultadoBusca(faixa=Faixa.MATCH, candidatos=[(transacao, 0.3)])
    )
    return busca


def _rag_ambiguo(candidatos: list[MagicMock]) -> MagicMock:
    from agent.services.rag import Faixa, ResultadoBusca  # type: ignore[import]

    busca = MagicMock()
    busca.buscar = AsyncMock(
        return_value=ResultadoBusca(
            faixa=Faixa.AMBIGUO,
            candidatos=[(c, 0.5 + i * 0.05) for i, c in enumerate(candidatos)],
        )
    )
    return busca


def _rag_piso() -> MagicMock:
    from agent.services.rag import Faixa, ResultadoBusca  # type: ignore[import]

    busca = MagicMock()
    busca.buscar = AsyncMock(
        return_value=ResultadoBusca(faixa=Faixa.PISO, candidatos=[])
    )
    return busca


def _repo_sem_parcelas_futuras() -> MagicMock:
    repo = MagicMock()
    repo.buscar_parcelas_futuras_grupo = AsyncMock(return_value=[])
    repo.contar_por_periodo_e_categoria = AsyncMock(return_value=0)
    repo.atualizar = AsyncMock()
    repo.excluir = AsyncMock()
    return repo


def _repo_com_parcelas_futuras(futuras: list[MagicMock]) -> MagicMock:
    repo = MagicMock()
    repo.buscar_parcelas_futuras_grupo = AsyncMock(return_value=futuras)
    repo.contar_por_periodo_e_categoria = AsyncMock(return_value=0)
    repo.atualizar = AsyncMock()
    repo.excluir = AsyncMock()
    return repo


def _repo_com_count_lote(qtd: int) -> MagicMock:
    repo = MagicMock()
    repo.buscar_parcelas_futuras_grupo = AsyncMock(return_value=[])
    repo.contar_por_periodo_e_categoria = AsyncMock(return_value=qtd)
    repo.atualizar = AsyncMock()
    repo.excluir = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# Import da tool (deve falhar enquanto o módulo não existir)
# ---------------------------------------------------------------------------


def _import_tool():
    from agent.tools.excluir import ToolExcluir  # type: ignore[import]
    return ToolExcluir


# ---------------------------------------------------------------------------
# Cenário: individual simples sem parcelas → aguardando_confirmacao
# ---------------------------------------------------------------------------


class TestExcluirIndividualSimples:
    async def test_individual_simples_gera_aguardando_confirmacao(self):
        """RAG MATCH + parcela_total=1 → aguardando_confirmacao com card do registro."""
        ToolExcluir = _import_tool()

        transacao = _make_transacao(
            descricao="Flores Natasha",
            valor=Decimal("140.00"),
            parcela_total=1,
        )
        rag = _rag_match(transacao)
        repo = _repo_sem_parcelas_futuras()

        params = ParamsExcluir(referencia="flores")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.acao == "excluir"
        assert resultado.status == "aguardando_confirmacao"
        assert resultado.dados["registro"]["descricao"] == "Flores Natasha"

    async def test_individual_simples_nao_persiste(self):
        """Tool nunca chama excluir no repository antes da confirmação."""
        ToolExcluir = _import_tool()

        transacao = _make_transacao(parcela_total=1)
        rag = _rag_match(transacao)
        repo = _repo_sem_parcelas_futuras()

        params = ParamsExcluir(referencia="flores")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        await tool.executar(params, usuario_id=1)

        repo.excluir.assert_not_called()

    async def test_individual_simples_dados_sem_modo_lote(self):
        """Exclusão individual não deve ter modo=lote nos dados."""
        ToolExcluir = _import_tool()

        transacao = _make_transacao(parcela_total=1)
        rag = _rag_match(transacao)
        repo = _repo_sem_parcelas_futuras()

        params = ParamsExcluir(referencia="flores")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.dados.get("modo") != "lote"


# ---------------------------------------------------------------------------
# Cenário: registro parcelado → aguardando_escopo com opções numeradas
# ---------------------------------------------------------------------------


class TestExcluirParcelado:
    async def test_parcelado_retorna_aguardando_escopo(self):
        """RAG MATCH + parcelas futuras → aguardando_escopo (1=somente este, 2=todos)."""
        ToolExcluir = _import_tool()

        transacao = _make_transacao(
            id=2,
            descricao="Batman PS5",
            valor=Decimal("200.00"),
            parcela_numero=2,
            parcela_total=4,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 6, 10),
            categoria=CategoriaEnum.LAZER,
        )

        futura_jul = _make_transacao(
            id=20, descricao="Batman PS5", parcela_numero=3, parcela_total=4,
            grupo_parcela_id=GRUPO_G1, data=date(2026, 7, 10),
        )
        futura_ago = _make_transacao(
            id=21, descricao="Batman PS5", parcela_numero=4, parcela_total=4,
            grupo_parcela_id=GRUPO_G1, data=date(2026, 8, 10),
        )
        futura_set = _make_transacao(
            id=22, descricao="Batman PS5", parcela_numero=4, parcela_total=4,
            grupo_parcela_id=GRUPO_G1, data=date(2026, 9, 10),
        )

        rag = _rag_match(transacao)
        repo = _repo_com_parcelas_futuras([futura_jul, futura_ago, futura_set])

        params = ParamsExcluir(referencia="batman")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.acao == "excluir"
        assert resultado.status == "aguardando_escopo"

    async def test_parcelado_lista_parcelas_futuras(self):
        """aguardando_escopo deve conter as parcelas futuras como rótulos."""
        ToolExcluir = _import_tool()

        transacao = _make_transacao(
            descricao="Batman PS5",
            parcela_numero=2,
            parcela_total=4,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 6, 10),
        )
        futura_jul = _make_transacao(
            id=10, parcela_numero=3, parcela_total=4,
            grupo_parcela_id=GRUPO_G1, data=date(2026, 7, 10),
        )
        futura_ago = _make_transacao(
            id=11, parcela_numero=4, parcela_total=4,
            grupo_parcela_id=GRUPO_G1, data=date(2026, 8, 10),
        )
        futura_set = _make_transacao(
            id=12, parcela_numero=4, parcela_total=4,
            grupo_parcela_id=GRUPO_G1, data=date(2026, 9, 10),
        )

        rag = _rag_match(transacao)
        repo = _repo_com_parcelas_futuras([futura_jul, futura_ago, futura_set])

        params = ParamsExcluir(referencia="batman")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        parcelas_futuras = resultado.dados["parcelas_futuras"]
        assert len(parcelas_futuras) == 3
        assert any("Jul" in r for r in parcelas_futuras)
        assert any("Ago" in r for r in parcelas_futuras)
        assert any("Set" in r for r in parcelas_futuras)

    async def test_parcelado_nao_persiste(self):
        """Tool parcelada nunca chama excluir antes da confirmação."""
        ToolExcluir = _import_tool()

        transacao = _make_transacao(
            parcela_numero=2, parcela_total=4, grupo_parcela_id=GRUPO_G1,
        )
        futura = _make_transacao(id=10, parcela_numero=3, grupo_parcela_id=GRUPO_G1)
        rag = _rag_match(transacao)
        repo = _repo_com_parcelas_futuras([futura])

        params = ParamsExcluir(referencia="batman")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        await tool.executar(params, usuario_id=1)

        repo.excluir.assert_not_called()


# ---------------------------------------------------------------------------
# Cenário: modo lote por periodo → count + aguardando_confirmacao
# ---------------------------------------------------------------------------


class TestExcluirModeLote:
    async def test_lote_por_periodo_retorna_aguardando_confirmacao(self):
        """Apenas período (sem referência) → mode lote: count + aguardando_confirmacao."""
        ToolExcluir = _import_tool()

        repo = _repo_com_count_lote(5)

        params = ParamsExcluir(periodo="2026-05")
        tool = ToolExcluir(rag=None, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.acao == "excluir"
        assert resultado.status == "aguardando_confirmacao"
        assert resultado.dados["modo"] == "lote"
        assert resultado.dados["qtd"] == 5

    async def test_lote_periodo_label_formatado(self):
        """periodo_label deve estar no formato Mês/AAAA (ex: Mai/2026)."""
        ToolExcluir = _import_tool()

        repo = _repo_com_count_lote(5)

        params = ParamsExcluir(periodo="2026-05")
        tool = ToolExcluir(rag=None, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        periodo_label = resultado.dados["periodo_label"]
        assert "Mai" in periodo_label or "2026" in periodo_label

    async def test_lote_nao_persiste(self):
        """Modo lote nunca chama excluir antes da confirmação."""
        ToolExcluir = _import_tool()

        repo = _repo_com_count_lote(3)

        params = ParamsExcluir(periodo="2026-05")
        tool = ToolExcluir(rag=None, repository=repo, relogio=_RELOGIO)
        await tool.executar(params, usuario_id=1)

        repo.excluir.assert_not_called()


# ---------------------------------------------------------------------------
# Cenário: AMBIGUO → aguardando_selecao com modo="individual"
# ---------------------------------------------------------------------------


class TestExcluirAmbiguo:
    async def test_ambiguo_retorna_aguardando_selecao(self):
        """RAG AMBIGUO → aguardando_selecao com modo='individual'."""
        ToolExcluir = _import_tool()

        c1 = _make_transacao(id=1, descricao="Internet Jun")
        c2 = _make_transacao(id=2, descricao="Internet Mai")
        rag = _rag_ambiguo([c1, c2])
        repo = _repo_sem_parcelas_futuras()

        params = ParamsExcluir(referencia="internet")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.acao == "excluir"
        assert resultado.status == "aguardando_selecao"
        assert resultado.dados["modo"] == "individual"

    async def test_ambiguo_opcoes_numeradas(self):
        """As opções em aguardando_selecao devem ser numeradas a partir de 1."""
        ToolExcluir = _import_tool()

        c1 = _make_transacao(id=1, descricao="Internet Jun")
        c2 = _make_transacao(id=2, descricao="Internet Mai")
        rag = _rag_ambiguo([c1, c2])
        repo = _repo_sem_parcelas_futuras()

        params = ParamsExcluir(referencia="internet")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        opcoes = resultado.dados["opcoes"]
        assert len(opcoes) == 2
        numeros = [op["numero"] for op in opcoes]
        assert numeros == [1, 2]


# ---------------------------------------------------------------------------
# Cenário: PISO → nao_encontrado
# ---------------------------------------------------------------------------


class TestExcluirPiso:
    async def test_piso_retorna_nao_encontrado(self):
        """RAG PISO → nao_encontrado com a referência original."""
        ToolExcluir = _import_tool()

        rag = _rag_piso()
        repo = _repo_sem_parcelas_futuras()

        params = ParamsExcluir(referencia="inexistente")
        tool = ToolExcluir(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.acao == "excluir"
        assert resultado.status == "nao_encontrado"
        assert resultado.dados["referencia"] == "inexistente"
