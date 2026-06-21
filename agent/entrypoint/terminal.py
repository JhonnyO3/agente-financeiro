"""
Modo terminal — roda o agente financeiro como chat no console.

Não requer WhatsApp nem Evolution API. Ideal para desenvolvimento e testes manuais.

Uso:
    uv run python -m agent.entrypoint.terminal
    uv run python -m agent.entrypoint.terminal --usuario 2
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Env mínimo antes de importar o agent
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_API_KEY", "placeholder")
os.environ.setdefault("EVOLUTION_INSTANCE", "placeholder")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "terminal@localhost")
os.environ.setdefault("REDIS_URL", os.environ.get("REDIS_URL", "redis://localhost:6379"))

from unittest.mock import AsyncMock

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agent.agents_llm import Embedder, criar_llm
from agent.config import settings
from agent.graph.builder import criar_grafo
from agent.services.classificador import Classificador
from agent.services.extrator import Extrator
from agent.services.formatador import Formatador
from agent.services.relogio import Relogio


class _RepoMock:
    """Repositório em memória — sem banco de dados."""

    def __init__(self) -> None:
        self._registros: list[dict] = []

    async def criar_lote(self, registros: list[dict], usuario_id: int | None = None) -> None:
        self._registros.extend(registros)

    async def listar_por_periodo(self, inicio, fim, usuario_id=None) -> list:
        return []

    async def listar_por_periodo_com_embedding(self, inicio, fim, usuario_id=None) -> list:
        return []

    async def agregar_por_categoria(self, inicio, fim, usuario_id=None) -> list:
        return []

    async def contar_por_filtros(self, inicio, fim, categoria=None, usuario_id=None) -> int:
        return 0

    async def buscar_semantico(self, embedding, limite=5, usuario_id=None) -> list:
        return []

    async def buscar_semantico_com_distancia(self, embedding, limite=1, usuario_id=None) -> list:
        return []

    async def buscar_semantico_multiplos_com_distancia(self, embedding, limite=5, usuario_id=None) -> list:
        return []

    async def atualizar(self, registro, diff, usuario_id=None) -> None:
        pass

    async def excluir(self, id, usuario_id=None) -> None:
        pass

    async def excluir_grupo(self, grupo_parcela_id, usuario_id=None) -> None:
        pass

    async def excluir_por_filtros(self, inicio, fim, categoria=None, usuario_id=None) -> None:
        pass

    async def buscar_por_grupo(self, grupo_parcela_id, usuario_id=None) -> list:
        return []


def _montar_grafo(repo: _RepoMock):
    """Monta o grafo com Evolution mockada e repositório em memória."""
    evolution = AsyncMock()
    evolution.enviar_mensagem = AsyncMock()

    grafo = criar_grafo(
        classificador=Classificador(),
        formatador=Formatador(),
        evolution=evolution,
        relogio=Relogio(settings.TIMEZONE_USUARIO),
        embedder=Embedder(),
        extrator=Extrator(llm=criar_llm()),
        repo_factory=lambda _: repo,
        checkpointer=MemorySaver(),
    )
    return grafo, evolution


async def _chat(usuario_id: int) -> None:
    repo = _RepoMock()
    grafo, evolution = _montar_grafo(repo)
    thread_id = f"terminal-{usuario_id}"

    print("\n" + "─" * 50)
    print("  Agente Financeiro — modo terminal")
    print("  (sem WhatsApp | Ctrl+C para sair)")
    print("─" * 50 + "\n")

    while True:
        try:
            entrada = input("você: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            break

        if not entrada:
            continue

        evolution.enviar_mensagem.reset_mock()

        try:
            await grafo.ainvoke(
                {
                    "messages": [HumanMessage(content=entrada)],
                    "usuario_id": usuario_id,
                    "numero": thread_id,
                },
                config={"configurable": {"thread_id": thread_id}},
            )
        except Exception as exc:
            print(f"agente: [erro interno: {exc}]\n")
            continue

        calls = evolution.enviar_mensagem.call_args_list
        resposta = calls[-1][0][1] if calls else "(sem resposta)"
        print(f"\nagente: {resposta}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente Financeiro — modo terminal")
    parser.add_argument("--usuario", type=int, default=1, help="ID do usuário (padrão: 1)")
    args = parser.parse_args()
    asyncio.run(_chat(args.usuario))


if __name__ == "__main__":
    main()
