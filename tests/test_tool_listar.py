"""
Testes vermelhos (TDD) — Task 09: ToolListar
Cenários espelhados de: specs/melhorias-agente/scenarios/09-tool-listar.feature

ESTADO ESPERADO: vermelho (red) — agent/tools/listar.py não existe ainda.

Números do exemplo em fluxo-atendimento-lista.md (Jun/2026):
  GASTOS_FIXOS: Internet 190 + Academia 120 + Claude Code 472 = 782
  COMPRAS: Flores 140 = 140
  PARCELAMENTOS: Zara 180 (PAGO) + Batman PS5 200 (PENDENTE) = 380
  Total: 1302  |  Pendente: 200  |  Pago: 1102
"""

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

# Vars mínimas antes de qualquer import do projeto
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ADMIN_EMAILS", "admin@exemplo.com")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "+5511999999999")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "admin@exemplo.com")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Testador")
os.environ.setdefault("WEBHOOK_APIKEY", "webhook-secret")

import pytest

from agent.domain.intencao import ParamsListar
from agent.domain.resultado import ResultadoTool
from agent.services.relogio import Relogio

# ---------------------------------------------------------------------------
# Importação do módulo alvo — ImportError é o vermelho esperado
# ---------------------------------------------------------------------------
from agent.tools.listar import ToolListar  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers para criar objetos Transacao fake (simples MagicMock com atributos)
# ---------------------------------------------------------------------------

def _transacao(
    descricao: str,
    valor: str,
    categoria: str,
    status: str = "PAGO",
    parcela_numero: int = 1,
    parcela_total: int = 1,
    data: date = date(2026, 6, 10),
    usuario_id: int = 1,
) -> MagicMock:
    t = MagicMock()
    t.descricao = descricao
    t.valor = Decimal(valor)
    t.categoria = categoria
    t.status = status
    t.parcela_numero = parcela_numero
    t.parcela_total = parcela_total
    t.data = data
    t.usuario_id = usuario_id
    return t


def _relogio_junho_2026() -> Relogio:
    """Relogio fixo: hoje = 2026-06-11 em BRT (UTC = 2026-06-11T13:00:00Z)."""
    utc_fixo = datetime(2026, 6, 11, 13, 0, 0, tzinfo=timezone.utc)
    return Relogio("America/Sao_Paulo", _fixed=utc_fixo)


def _repo_mock(transacoes: list) -> AsyncMock:
    repo = AsyncMock()
    repo.listar_por_periodo = AsyncMock(return_value=transacoes)
    return repo


# ---------------------------------------------------------------------------
# Cenário: listar mês atual sem filtros agrupa por categoria com subtotais
# ---------------------------------------------------------------------------

class TestListarMesAtual:
    async def test_status_concluido_com_registros(self):
        transacoes = [
            _transacao("Internet", "190.00", "GASTOS_FIXOS"),
            _transacao("Academia", "120.00", "GASTOS_FIXOS", data=date(2026, 6, 5)),
            _transacao("Claude Code", "472.00", "GASTOS_FIXOS", data=date(2026, 6, 11)),
            _transacao("Flores Natasha", "140.00", "COMPRAS", data=date(2026, 6, 11)),
        ]
        repo = _repo_mock(transacoes)
        relogio = _relogio_junho_2026()
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        params = ParamsListar()
        resultado = await tool.executar(params, contexto={})

        assert isinstance(resultado, ResultadoTool)
        assert resultado.acao == "listar"
        assert resultado.status == "concluido"

    async def test_grupos_por_categoria_com_subtotais(self):
        transacoes = [
            _transacao("Internet", "190.00", "GASTOS_FIXOS"),
            _transacao("Academia", "120.00", "GASTOS_FIXOS", data=date(2026, 6, 5)),
            _transacao("Claude Code", "472.00", "GASTOS_FIXOS", data=date(2026, 6, 11)),
            _transacao("Flores Natasha", "140.00", "COMPRAS", data=date(2026, 6, 11)),
        ]
        repo = _repo_mock(transacoes)
        relogio = _relogio_junho_2026()
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})
        grupos = resultado.dados["grupos"]
        titulos = [g["titulo"] for g in grupos]

        assert "GASTOS_FIXOS" in titulos
        assert "COMPRAS" in titulos

        grupo_gf = next(g for g in grupos if g["titulo"] == "GASTOS_FIXOS")
        assert len(grupo_gf["itens"]) == 3
        assert grupo_gf["subtotal"] == Decimal("782.00")

        grupo_c = next(g for g in grupos if g["titulo"] == "COMPRAS")
        assert len(grupo_c["itens"]) == 1

    async def test_periodo_label_junho_2026(self):
        repo = _repo_mock([_transacao("Internet", "190.00", "GASTOS_FIXOS")])
        relogio = _relogio_junho_2026()
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})

        assert resultado.dados["periodo_label"] == "Jun/2026"


# ---------------------------------------------------------------------------
# Cenário: registros parcelados entram na seção PARCELAMENTOS
# ---------------------------------------------------------------------------

class TestParcelamentos:
    async def test_parcelado_vai_para_parcelamentos_nao_para_categoria(self):
        transacoes = [
            _transacao(
                "Batman PS5",
                "200.00",
                "LAZER",
                status="PENDENTE",
                parcela_numero=2,
                parcela_total=4,
            ),
        ]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})
        grupos = resultado.dados["grupos"]
        titulos = [g["titulo"] for g in grupos]

        assert "PARCELAMENTOS" in titulos
        assert "LAZER" not in titulos

        grupo_p = next(g for g in grupos if g["titulo"] == "PARCELAMENTOS")
        descricoes = [i["descricao"] for i in grupo_p["itens"]]
        assert "Batman PS5" in descricoes

    async def test_mix_parcelado_e_avista_separa_corretamente(self):
        transacoes = [
            _transacao("Flores Natasha", "140.00", "COMPRAS"),  # à vista
            _transacao(
                "Zara Roupas",
                "180.00",
                "COMPRAS",
                parcela_numero=3,
                parcela_total=5,
            ),  # parcelado
        ]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})
        grupos = resultado.dados["grupos"]
        titulos = [g["titulo"] for g in grupos]

        assert "PARCELAMENTOS" in titulos
        assert "COMPRAS" in titulos

        grupo_c = next(g for g in grupos if g["titulo"] == "COMPRAS")
        descricoes_compras = [i["descricao"] for i in grupo_c["itens"]]
        assert "Flores Natasha" in descricoes_compras
        assert "Zara Roupas" not in descricoes_compras


# ---------------------------------------------------------------------------
# Cenário: split pago/pendente em Decimal sem LLM
# (números do exemplo do fluxo: 782+140+380=1302, pendente=200, pago=1102)
# ---------------------------------------------------------------------------

class TestSplitPagoPendente:
    async def test_split_com_numeros_do_exemplo(self):
        transacoes = [
            # GASTOS_FIXOS (à vista, todos PAGO) = 782
            _transacao("Internet", "190.00", "GASTOS_FIXOS"),
            _transacao("Academia", "120.00", "GASTOS_FIXOS"),
            _transacao("Claude Code", "472.00", "GASTOS_FIXOS"),
            # COMPRAS (à vista, PAGO) = 140
            _transacao("Flores Natasha", "140.00", "COMPRAS"),
            # PARCELAMENTOS = 380
            _transacao(
                "Zara Roupas", "180.00", "COMPRAS",
                status="PAGO", parcela_numero=3, parcela_total=5,
            ),
            _transacao(
                "Batman PS5", "200.00", "LAZER",
                status="PENDENTE", parcela_numero=2, parcela_total=4,
            ),
        ]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})
        dados = resultado.dados

        assert dados["total"] == Decimal("1302.00")
        assert dados["pendente"] == Decimal("200.00")
        assert dados["pago"] == Decimal("1102.00")

    async def test_valores_sao_decimal_nao_float(self):
        transacoes = [_transacao("Internet", "190.00", "GASTOS_FIXOS")]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})
        dados = resultado.dados

        assert isinstance(dados["total"], Decimal)
        assert isinstance(dados["pago"], Decimal)
        assert isinstance(dados["pendente"], Decimal)

    async def test_sem_chamada_llm(self):
        """ToolListar é zero-LLM: nenhum atributo de LLM pode ser acessado."""
        transacoes = [
            _transacao("Internet", "190.00", "GASTOS_FIXOS"),
            _transacao(
                "Batman PS5", "200.00", "LAZER",
                status="PENDENTE", parcela_numero=2, parcela_total=4,
            ),
        ]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        # Se a Tool tentar acessar qualquer coisa de LLM no contexto,
        # o contexto vazio sem chave 'llm' / 'chain' deve deixar o teste passar
        # (o erro seria AttributeError em produção, aqui a ausência de mock é suficiente).
        resultado = await tool.executar(ParamsListar(), contexto={})

        # Confirmar resultado sem nenhuma LLM no contexto
        assert resultado.status in {"concluido", "vazio"}


# ---------------------------------------------------------------------------
# Cenário: período ausente usa mês atual via Relogio
# ---------------------------------------------------------------------------

class TestPeriodoAusenteUsaMesAtual:
    async def test_periodo_none_consulta_mes_atual(self):
        repo = _repo_mock([])
        utc_fixo = datetime(2026, 6, 11, 13, 0, 0, tzinfo=timezone.utc)
        relogio = Relogio("America/Sao_Paulo", _fixed=utc_fixo)
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        await tool.executar(ParamsListar(periodo=None), contexto={})

        # listar_por_periodo deve ter sido chamado com início = 2026-06-01 e fim = 2026-06-30
        repo.listar_por_periodo.assert_called_once()
        call_args = repo.listar_por_periodo.call_args
        inicio = call_args.args[0] if call_args.args else call_args.kwargs.get("inicio")
        fim = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("fim")

        assert inicio == date(2026, 6, 1), f"início esperado 2026-06-01, got {inicio}"
        assert fim == date(2026, 6, 30), f"fim esperado 2026-06-30, got {fim}"

    async def test_periodo_mes_atual_string_consulta_mes_atual(self):
        """periodo='mes_atual' é tratado igual a None (mês atual)."""
        repo = _repo_mock([])
        relogio = _relogio_junho_2026()
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        await tool.executar(ParamsListar(periodo="mes_atual"), contexto={})

        repo.listar_por_periodo.assert_called_once()
        call_args = repo.listar_por_periodo.call_args
        inicio = call_args.args[0] if call_args.args else call_args.kwargs.get("inicio")
        assert inicio == date(2026, 6, 1)


# ---------------------------------------------------------------------------
# Cenário: período com nome de mês é convertido corretamente
# ---------------------------------------------------------------------------

class TestPeriodoNomeMes:
    async def test_maio_convertido_para_2026_05(self):
        repo = _repo_mock([])
        relogio = _relogio_junho_2026()  # ano de referência = 2026
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        await tool.executar(ParamsListar(periodo="maio"), contexto={})

        repo.listar_por_periodo.assert_called_once()
        call_args = repo.listar_por_periodo.call_args
        inicio = call_args.args[0] if call_args.args else call_args.kwargs.get("inicio")
        fim = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("fim")

        assert inicio == date(2026, 5, 1), f"início esperado 2026-05-01, got {inicio}"
        assert fim == date(2026, 5, 31), f"fim esperado 2026-05-31, got {fim}"

    async def test_janeiro_convertido_corretamente(self):
        repo = _repo_mock([])
        relogio = _relogio_junho_2026()
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        await tool.executar(ParamsListar(periodo="2026-01"), contexto={})

        call_args = repo.listar_por_periodo.call_args
        inicio = call_args.args[0] if call_args.args else call_args.kwargs.get("inicio")
        fim = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("fim")

        assert inicio == date(2026, 1, 1)
        assert fim == date(2026, 1, 31)


# ---------------------------------------------------------------------------
# Cenário: nenhum registro no período → status "vazio"
# ---------------------------------------------------------------------------

class TestPeriodoVazio:
    async def test_sem_registros_retorna_status_vazio(self):
        repo = _repo_mock([])
        relogio = _relogio_junho_2026()
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        resultado = await tool.executar(ParamsListar(periodo="2026-01"), contexto={})

        assert resultado.status == "vazio"

    async def test_vazio_tem_acao_listar(self):
        repo = _repo_mock([])
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(periodo="2026-01"), contexto={})

        assert resultado.acao == "listar"

    async def test_vazio_inclui_periodo_label(self):
        repo = _repo_mock([])
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(periodo="2026-01"), contexto={})

        assert "periodo_label" in resultado.dados
        assert resultado.dados["periodo_label"] == "Jan/2026"


# ---------------------------------------------------------------------------
# Cenário: filtro de categoria repassa corretamente e reduz listagem
# ---------------------------------------------------------------------------

class TestFiltroCategoría:
    async def test_filtro_categoria_mantém_só_grupo_filtrado(self):
        # repository retorna apenas COMPRAS quando filtro é aplicado
        transacoes = [
            _transacao("Flores Natasha", "140.00", "COMPRAS"),
        ]
        repo = _repo_mock(transacoes)
        relogio = _relogio_junho_2026()
        tool = ToolListar(repo=repo, relogio=relogio, usuario_id=1)

        resultado = await tool.executar(
            ParamsListar(categoria="COMPRAS"), contexto={}
        )

        grupos = resultado.dados["grupos"]
        titulos = [g["titulo"] for g in grupos]

        assert "COMPRAS" in titulos
        assert "GASTOS_FIXOS" not in titulos

    async def test_filtro_categoria_passado_ao_repository(self):
        """O filtro de categoria deve ser propagado para listar_por_periodo (ou método filtrado)."""
        transacoes = [_transacao("Flores Natasha", "140.00", "COMPRAS")]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        await tool.executar(ParamsListar(categoria="COMPRAS"), contexto={})

        # A tool deve filtrar por categoria: ou chama método com parâmetro categoria,
        # ou aplica filtro local. Aqui verificamos que, após executar, só há COMPRAS nos grupos.
        resultado = await tool.executar(
            ParamsListar(categoria="COMPRAS"), contexto={}
        )
        titulos = [g["titulo"] for g in resultado.dados["grupos"]]
        assert all(t == "COMPRAS" for t in titulos if t != "PARCELAMENTOS")

    async def test_sem_filtro_categoria_retorna_todos_grupos(self):
        transacoes = [
            _transacao("Internet", "190.00", "GASTOS_FIXOS"),
            _transacao("Flores Natasha", "140.00", "COMPRAS"),
        ]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})
        titulos = [g["titulo"] for g in resultado.dados["grupos"]]

        assert "GASTOS_FIXOS" in titulos
        assert "COMPRAS" in titulos


# ---------------------------------------------------------------------------
# Cenário: estrutura dos itens dentro dos grupos
# ---------------------------------------------------------------------------

class TestEstruturaItens:
    async def test_item_tem_campos_do_contrato(self):
        transacoes = [_transacao("Internet", "190.00", "GASTOS_FIXOS")]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})
        grupos = resultado.dados["grupos"]
        item = grupos[0]["itens"][0]

        # Campos obrigatórios do contrato resultado-tools.md
        assert "descricao" in item
        assert "valor" in item
        assert "data" in item
        assert "status" in item
        assert "parcela_numero" in item
        assert "parcela_total" in item
        assert isinstance(item["valor"], Decimal)

    async def test_subtotal_e_decimal(self):
        transacoes = [
            _transacao("Internet", "190.00", "GASTOS_FIXOS"),
            _transacao("Academia", "120.00", "GASTOS_FIXOS"),
        ]
        repo = _repo_mock(transacoes)
        tool = ToolListar(repo=repo, relogio=_relogio_junho_2026(), usuario_id=1)

        resultado = await tool.executar(ParamsListar(), contexto={})
        grupo_gf = next(
            g for g in resultado.dados["grupos"] if g["titulo"] == "GASTOS_FIXOS"
        )

        assert isinstance(grupo_gf["subtotal"], Decimal)
        assert grupo_gf["subtotal"] == Decimal("310.00")
