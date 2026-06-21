from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from agent.graph.edges import rotear
from agent.graph.nodes import (
    criar_no_classificar,
    criar_no_enviar,
    criar_no_formatar,
    criar_no_operacao,
)
from agent.graph.operacoes.cadastrar import Cadastrar
from agent.graph.operacoes.conversar import Conversar
from agent.graph.operacoes.excluir import Excluir
from agent.graph.operacoes.listar import Listar
from agent.graph.operacoes.atualizar import Atualizar
from agent.graph.state import AgentState

if TYPE_CHECKING:
    from collections.abc import Callable
    from langgraph.graph.state import CompiledStateGraph
    from agent.agents_llm import Embedder
    from agent.integrations.evolution_client import EvolutionApiClient
    from agent.services.classificador import Classificador
    from agent.services.extrator import Extrator
    from agent.services.formatador import Formatador
    from agent.services.relogio import Relogio


def criar_grafo(
    *,
    classificador: Classificador,
    formatador: Formatador,
    evolution: EvolutionApiClient,
    relogio: Relogio,
    embedder: Embedder,
    extrator: Extrator,
    repo_factory: Callable,
    checkpointer=None,
) -> CompiledStateGraph:
    cadastrar = Cadastrar(relogio=relogio, repo_factory=repo_factory, extrator=extrator, embedder=embedder)
    listar = Listar(relogio=relogio, repo_factory=repo_factory)
    atualizar = Atualizar(relogio=relogio, repo_factory=repo_factory, embedder=embedder)
    excluir = Excluir(relogio=relogio, repo_factory=repo_factory, embedder=embedder)
    conversar = Conversar()

    graph = StateGraph(AgentState)

    graph.add_node("no_classificar", criar_no_classificar(classificador))
    graph.add_node("no_cadastrar", criar_no_operacao(cadastrar))
    graph.add_node("no_listar", criar_no_operacao(listar))
    graph.add_node("no_atualizar", criar_no_operacao(atualizar))
    graph.add_node("no_excluir", criar_no_operacao(excluir))
    graph.add_node("no_conversar", criar_no_operacao(conversar))
    graph.add_node("no_formatar", criar_no_formatar(formatador))
    graph.add_node("no_enviar", criar_no_enviar(evolution))

    graph.set_entry_point("no_classificar")

    graph.add_conditional_edges(
        "no_classificar",
        rotear,
        {
            "no_cadastrar": "no_cadastrar",
            "no_listar": "no_listar",
            "no_atualizar": "no_atualizar",
            "no_excluir": "no_excluir",
            "no_conversar": "no_conversar",
        },
    )

    for no_op in ("no_cadastrar", "no_listar", "no_atualizar", "no_excluir", "no_conversar"):
        graph.add_edge(no_op, "no_formatar")

    graph.add_edge("no_formatar", "no_enviar")
    graph.add_edge("no_enviar", END)

    return graph.compile(checkpointer=checkpointer)
