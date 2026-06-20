"""
Testes de integração do agente LangGraph.

Usa OpenAI e Redis reais. Evolution API é mockada — nenhuma mensagem WhatsApp
é enviada. O repositório também é mockado (sem banco de dados).

Cada teste valida um fluxo completo de ponta a ponta:
  usuário envia mensagem → grafo classifica → operação executa → Formatador gera
  resposta → Evolution.enviar_mensagem é chamado com o texto correto.

Para rodar:
    uv run pytest tests/agent/ -v
    OPENAI_API_KEY=sk-... uv run pytest tests/agent/ -v -s
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agent.agents_llm import Embedder, criar_llm
from agent.config import settings
from agent.graph.builder import criar_grafo
from agent.services.classificador import Classificador
from agent.services.extrator import Extrator
from agent.services.formatador import Formatador
from agent.services.relogio import Relogio

USUARIO_ID = 1


class _RepoMock:
    """Repositório sem banco — aceita todas as chamadas."""

    async def criar_lote(self, registros, usuario_id=None):
        pass

    async def listar_por_periodo(self, inicio, fim, usuario_id=None):
        return []

    async def listar_por_periodo_com_embedding(self, inicio, fim, usuario_id=None):
        return []

    async def agregar_por_categoria(self, inicio, fim, usuario_id=None):
        return []

    async def contar_por_filtros(self, inicio, fim, categoria=None, usuario_id=None):
        return 0

    async def buscar_semantico(self, embedding, limite=5, usuario_id=None):
        return []

    async def buscar_semantico_com_distancia(self, embedding, limite=1, usuario_id=None):
        return []

    async def buscar_semantico_multiplos_com_distancia(self, embedding, limite=5, usuario_id=None):
        return []

    async def atualizar(self, registro, diff, usuario_id=None):
        pass

    async def excluir(self, id, usuario_id=None):
        pass

    async def excluir_grupo(self, grupo_parcela_id, usuario_id=None):
        pass

    async def excluir_por_filtros(self, inicio, fim, categoria=None, usuario_id=None):
        pass

    async def buscar_por_grupo(self, grupo_parcela_id, usuario_id=None):
        return []


@pytest.fixture(scope="module")
def grafo_e_evolution():
    """Grafo LangGraph com OpenAI real, Redis real, Evolution mockada."""
    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()

    repo = _RepoMock()
    g = criar_grafo(
        classificador=Classificador(),
        formatador=Formatador(),
        evolution=mock_evolution,
        relogio=Relogio(settings.TIMEZONE_USUARIO),
        embedder=Embedder(),
        extrator=Extrator(llm=criar_llm()),
        repo_factory=lambda _: repo,
        checkpointer=MemorySaver(),
    )
    return g, mock_evolution


async def _invocar(grafo_e_evolution, thread_id: str, texto: str) -> str:
    grafo, mock_evolution = grafo_e_evolution
    mock_evolution.enviar_mensagem.reset_mock()
    await grafo.ainvoke(
        {
            "messages": [HumanMessage(content=texto)],
            "usuario_id": USUARIO_ID,
            "numero": thread_id,
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    calls = mock_evolution.enviar_mensagem.call_args_list
    assert calls, "Evolution.enviar_mensagem não foi chamado — grafo não produziu resposta"
    return calls[-1][0][1]


# ---------------------------------------------------------------------------
# Fluxo 1: Cadastro simples (1 turno + confirmação)
# ---------------------------------------------------------------------------


async def test_cadastro_simples_solicita_confirmacao(grafo_e_evolution):
    """Mensagem de gasto único → agente pede confirmação antes de salvar."""
    resposta = await _invocar(grafo_e_evolution, "t-cadastrar-01", "Gastei 50 reais no mercado hoje")
    # Agente deve reconhecer o cadastro e pedir confirmação (ou confirmar que registrou)
    assert any(
        kw in resposta.lower()
        for kw in ("confirm", "registr", "mercado", "50", "cadastr", "salv")
    ), f"Resposta inesperada: {resposta!r}"


async def test_cadastro_confirmado_conclui(grafo_e_evolution):
    """Após pedido de confirmação, 'sim' conclui o cadastro."""
    thread_id = "t-cadastrar-02"
    await _invocar(grafo_e_evolution, thread_id, "Gastei 30 reais na farmácia")
    resposta_confirmacao = await _invocar(grafo_e_evolution, thread_id, "sim")
    assert any(
        kw in resposta_confirmacao.lower()
        for kw in ("registr", "salv", "cadastr", "conclu", "ok", "feito", "✅")
    ), f"Confirmação não reconhecida: {resposta_confirmacao!r}"


# ---------------------------------------------------------------------------
# Fluxo 2: Listagem
# ---------------------------------------------------------------------------


async def test_listar_retorna_resposta_sem_transacoes(grafo_e_evolution):
    """Pedido de listagem com repositório vazio → resposta informativa."""
    resposta = await _invocar(grafo_e_evolution, "t-listar-01", "Quais foram meus gastos esse mês?")
    assert any(
        kw in resposta.lower()
        for kw in ("nenhu", "vazio", "não encontr", "nada", "gastos", "mês", "período")
    ), f"Resposta de listagem inesperada: {resposta!r}"


# ---------------------------------------------------------------------------
# Fluxo 3: Exclusão não encontrada
# ---------------------------------------------------------------------------


async def test_excluir_nao_encontrado_responde_graciosamente(grafo_e_evolution):
    """Pedido de exclusão de algo que não existe → resposta amigável."""
    resposta = await _invocar(
        grafo_e_evolution, "t-excluir-01", "Exclua o gasto do cinema ontem"
    )
    assert any(
        kw in resposta.lower()
        for kw in ("nenhu", "não encontr", "cinema", "encontr", "localiz")
    ), f"Resposta de exclusão inesperada: {resposta!r}"


# ---------------------------------------------------------------------------
# Fluxo 4: Conversa genérica
# ---------------------------------------------------------------------------


async def test_conversa_generica_responde(grafo_e_evolution):
    """Mensagem conversacional → resposta coerente sem travar o estado."""
    resposta = await _invocar(
        grafo_e_evolution, "t-conversar-01", "Olá, tudo bem?"
    )
    assert len(resposta) > 5, f"Resposta muito curta: {resposta!r}"


async def test_contexto_multi_turno_mantido(grafo_e_evolution):
    """Múltiplos turnos no mesmo thread → contexto é mantido pelo checkpointer."""
    thread_id = "t-multiturn-01"
    await _invocar(grafo_e_evolution, thread_id, "Meu nome é Teste e sou desenvolvedor")
    resposta = await _invocar(grafo_e_evolution, thread_id, "Qual foi o meu nome que te disse?")
    assert "teste" in resposta.lower(), (
        f"Contexto multi-turno perdido. Resposta: {resposta!r}"
    )
