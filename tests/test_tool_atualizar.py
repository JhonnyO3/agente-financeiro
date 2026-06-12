"""
Testes vermelhos (TDD) — Task 10: ToolAtualizar
Cenários espelhados de: specs/melhorias-agente/scenarios/10-tools-atualizar-excluir.feature

ESTADO ESPERADO: vermelho (red) — agent/tools/atualizar.py ainda não existe.
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
from agent.domain.intencao import ParamsAtualizar
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
    descricao: str = "Internet",
    valor: Decimal = Decimal("190.00"),
    data: date = date(2026, 6, 10),
    categoria: CategoriaEnum = CategoriaEnum.GASTOS_FIXOS,
    forma_pagamento: FormaPagamentoEnum = FormaPagamentoEnum.PIX,
    status: StatusEnum = StatusEnum.PENDENTE,
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
    """Cria BuscaRAG mockado retornando MATCH com 1 candidato."""
    from agent.services.rag import Faixa, ResultadoBusca  # type: ignore[import]

    busca = MagicMock()
    busca.buscar = AsyncMock(
        return_value=ResultadoBusca(faixa=Faixa.MATCH, candidatos=[(transacao, 0.3)])
    )
    return busca


def _rag_ambiguo(candidatos: list[MagicMock]) -> MagicMock:
    """Cria BuscaRAG mockado retornando AMBIGUO com vários candidatos."""
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
    """Cria BuscaRAG mockado retornando PISO."""
    from agent.services.rag import Faixa, ResultadoBusca  # type: ignore[import]

    busca = MagicMock()
    busca.buscar = AsyncMock(
        return_value=ResultadoBusca(faixa=Faixa.PISO, candidatos=[])
    )
    return busca


def _repo_sem_parcelas_futuras() -> MagicMock:
    repo = MagicMock()
    repo.buscar_parcelas_futuras_grupo = AsyncMock(return_value=[])
    repo.atualizar = AsyncMock()
    repo.excluir = AsyncMock()
    return repo


def _repo_com_parcelas_futuras(grupo_id: str, futuras: list[MagicMock]) -> MagicMock:
    repo = MagicMock()
    repo.buscar_parcelas_futuras_grupo = AsyncMock(return_value=futuras)
    repo.atualizar = AsyncMock()
    repo.excluir = AsyncMock()
    return repo


# ---------------------------------------------------------------------------
# Import da tool (deve falhar enquanto o módulo não existir)
# ---------------------------------------------------------------------------

def _import_tool():
    from agent.tools.atualizar import ToolAtualizar  # type: ignore[import]
    return ToolAtualizar


# ---------------------------------------------------------------------------
# Cenário: MATCH com status gera diff aguardando_confirmacao
# ---------------------------------------------------------------------------


class TestAtualizarMatch:
    async def test_match_status_gera_diff_aguardando_confirmacao(self):
        """RAG MATCH + campo=status → aguardando_confirmacao com diff antigo/novo."""
        ToolAtualizar = _import_tool()

        transacao = _make_transacao(
            descricao="Internet", status=StatusEnum.PENDENTE
        )
        rag = _rag_match(transacao)
        repo = _repo_sem_parcelas_futuras()

        params = ParamsAtualizar(
            referencia="internet", campo="status", novo_valor="PAGO"
        )
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.acao == "atualizar"
        assert resultado.status == "aguardando_confirmacao"
        diff = resultado.dados["diff"]
        assert diff["campo"] == "status"
        assert diff["antigo"] == "PENDENTE"
        assert diff["novo"] == "PAGO"

    async def test_match_nao_persiste_no_banco(self):
        """Tool nunca chama atualizar no repository — persistência ocorre no confirmar."""
        ToolAtualizar = _import_tool()

        transacao = _make_transacao(status=StatusEnum.PENDENTE)
        rag = _rag_match(transacao)
        repo = _repo_sem_parcelas_futuras()

        params = ParamsAtualizar(
            referencia="internet", campo="status", novo_valor="PAGO"
        )
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        await tool.executar(params, usuario_id=1)

        repo.atualizar.assert_not_called()

    async def test_match_dados_contem_registro(self):
        """dados['registro'] deve conter as informações do registro encontrado."""
        ToolAtualizar = _import_tool()

        transacao = _make_transacao(descricao="Internet", valor=Decimal("190.00"))
        rag = _rag_match(transacao)
        repo = _repo_sem_parcelas_futuras()

        params = ParamsAtualizar(
            referencia="internet", campo="valor", novo_valor="200"
        )
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert "registro" in resultado.dados
        assert resultado.dados["registro"]["descricao"] == "Internet"


# ---------------------------------------------------------------------------
# Cenário: AMBIGUO gera aguardando_selecao com opções numeradas
# ---------------------------------------------------------------------------


class TestAtualizarAmbiguo:
    async def test_ambiguo_retorna_aguardando_selecao(self):
        """RAG AMBIGUO → aguardando_selecao com lista de opcoes."""
        ToolAtualizar = _import_tool()

        c1 = _make_transacao(id=1, descricao="Roupas Zara")
        c2 = _make_transacao(id=2, descricao="Batman PS5")
        rag = _rag_ambiguo([c1, c2])
        repo = _repo_sem_parcelas_futuras()

        params = ParamsAtualizar(referencia="cartao", campo="valor", novo_valor="100")
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.acao == "atualizar"
        assert resultado.status == "aguardando_selecao"
        opcoes = resultado.dados["opcoes"]
        assert len(opcoes) == 2

    async def test_ambiguo_opcoes_sao_numeradas(self):
        """Cada opção deve ter número sequencial a partir de 1."""
        ToolAtualizar = _import_tool()

        c1 = _make_transacao(id=1, descricao="Roupas Zara")
        c2 = _make_transacao(id=2, descricao="Batman PS5")
        rag = _rag_ambiguo([c1, c2])
        repo = _repo_sem_parcelas_futuras()

        params = ParamsAtualizar(referencia="cartao", campo="valor", novo_valor="100")
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        numeros = [op["numero"] for op in resultado.dados["opcoes"]]
        assert numeros == [1, 2]


# ---------------------------------------------------------------------------
# Cenário: PISO retorna nao_encontrado
# ---------------------------------------------------------------------------


class TestAtualizarPiso:
    async def test_piso_retorna_nao_encontrado(self):
        """RAG PISO → nao_encontrado com a referência original."""
        ToolAtualizar = _import_tool()

        rag = _rag_piso()
        repo = _repo_sem_parcelas_futuras()

        params = ParamsAtualizar(
            referencia="inexistente", campo="valor", novo_valor="100"
        )
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.acao == "atualizar"
        assert resultado.status == "nao_encontrado"
        assert resultado.dados["referencia"] == "inexistente"


# ---------------------------------------------------------------------------
# Cenário: campo=valor com parcelas futuras propaga e lista afetadas
# ---------------------------------------------------------------------------


class TestAtualizarPropagacaoValor:
    async def test_campo_valor_com_parcelas_futuras_lista_afetadas(self):
        """Campo valor + parcelas futuras → parcelas_afetadas preenchido."""
        ToolAtualizar = _import_tool()

        transacao = _make_transacao(
            descricao="Roupas Zara",
            valor=Decimal("180.00"),
            parcela_numero=3,
            parcela_total=5,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 6, 10),
        )

        # Parcelas futuras Jul/26 e Ago/26
        futura_jul = _make_transacao(
            id=10,
            descricao="Roupas Zara",
            valor=Decimal("180.00"),
            parcela_numero=4,
            parcela_total=5,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 7, 10),
        )
        futura_ago = _make_transacao(
            id=11,
            descricao="Roupas Zara",
            valor=Decimal("180.00"),
            parcela_numero=5,
            parcela_total=5,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 8, 10),
        )

        rag = _rag_match(transacao)
        repo = _repo_com_parcelas_futuras(GRUPO_G1, [futura_jul, futura_ago])

        params = ParamsAtualizar(
            referencia="zara", campo="valor", novo_valor="200"
        )
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.status == "aguardando_confirmacao"
        parcelas_afetadas = resultado.dados["parcelas_afetadas"]
        assert len(parcelas_afetadas) == 2
        # Rótulos no formato Mês/AA
        assert any("Jul" in r for r in parcelas_afetadas)
        assert any("Ago" in r for r in parcelas_afetadas)

    async def test_campo_valor_sem_parcelas_futuras_lista_vazia(self):
        """Campo valor sem parcelas futuras → parcelas_afetadas vazio."""
        ToolAtualizar = _import_tool()

        transacao = _make_transacao(
            descricao="Internet",
            valor=Decimal("190.00"),
            parcela_numero=1,
            parcela_total=1,
        )
        rag = _rag_match(transacao)
        repo = _repo_sem_parcelas_futuras()

        params = ParamsAtualizar(
            referencia="internet", campo="valor", novo_valor="200"
        )
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.dados.get("parcelas_afetadas", []) == []


# ---------------------------------------------------------------------------
# Cenário: campo=data com parcelas futuras propaga
# ---------------------------------------------------------------------------


class TestAtualizarPropagacaoData:
    async def test_campo_data_com_parcelas_futuras_retorna_afetadas(self):
        """Campo data + parcelas futuras → parcelas_afetadas não vazio."""
        ToolAtualizar = _import_tool()

        transacao = _make_transacao(
            descricao="Netflix",
            parcela_numero=2,
            parcela_total=4,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 6, 15),
        )

        futura_jul = _make_transacao(
            id=20,
            descricao="Netflix",
            parcela_numero=3,
            parcela_total=4,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 7, 15),
        )
        futura_ago = _make_transacao(
            id=21,
            descricao="Netflix",
            parcela_numero=4,
            parcela_total=4,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 8, 15),
        )

        rag = _rag_match(transacao)
        repo = _repo_com_parcelas_futuras(GRUPO_G1, [futura_jul, futura_ago])

        params = ParamsAtualizar(
            referencia="netflix", campo="data", novo_valor="15/07/2026"
        )
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.status == "aguardando_confirmacao"
        assert len(resultado.dados.get("parcelas_afetadas", [])) > 0


# ---------------------------------------------------------------------------
# Cenário: campo=status NÃO propaga para parcelas futuras
# ---------------------------------------------------------------------------


class TestAtualizarStatusSemPropagacao:
    async def test_campo_status_nao_propaga(self):
        """Campo status → parcelas_afetadas deve ser lista vazia (sem propagação)."""
        ToolAtualizar = _import_tool()

        transacao = _make_transacao(
            descricao="Financiamento",
            status=StatusEnum.PENDENTE,
            parcela_numero=3,
            parcela_total=10,
            grupo_parcela_id=GRUPO_G1,
        )

        # Mesmo que existam parcelas futuras no grupo, status não deve propagá-las
        futura = _make_transacao(
            id=30,
            descricao="Financiamento",
            parcela_numero=4,
            parcela_total=10,
            grupo_parcela_id=GRUPO_G1,
            data=date(2026, 7, 10),
        )

        rag = _rag_match(transacao)
        # Repository possui parcelas, mas a tool NÃO deve consultá-las para status
        repo = _repo_com_parcelas_futuras(GRUPO_G1, [futura])

        params = ParamsAtualizar(
            referencia="financiamento", campo="status", novo_valor="PAGO"
        )
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=_RELOGIO)
        resultado: ResultadoTool = await tool.executar(params, usuario_id=1)

        assert resultado.status == "aguardando_confirmacao"
        assert resultado.dados.get("parcelas_afetadas", []) == []
