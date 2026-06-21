"""
Modo terminal — roda o agente financeiro como chat no console.

Usa o fluxo completo (DB real, OpenAI real, Redis real). A única diferença
é que as respostas são impressas no terminal em vez de enviadas via WhatsApp.

Uso:
    uv run python -m agent.entrypoint.terminal
    uv run python -m agent.entrypoint.terminal --usuario 1
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env", encoding="utf-8-sig")

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from agent.agents_llm import Embedder, criar_llm
from agent.config import settings
from agent.entrypoint.main import _criar_repo_factory
from agent.graph.builder import criar_grafo
from agent.services.classificador import Classificador
from agent.services.extrator import Extrator
from agent.services.formatador import Formatador
from agent.services.relogio import Relogio


class _TerminalEvolution:
    """Substitui Evolution API: imprime a resposta no terminal."""

    def __init__(self) -> None:
        self._ultima_resposta: str = ""

    async def enviar_mensagem(self, numero: str, mensagem: str) -> None:
        self._ultima_resposta = mensagem
        print(f"\nagente: {mensagem}\n")

    async def fechar(self) -> None:
        pass


async def _chat(usuario_id: int) -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    repo_factory = _criar_repo_factory(session_factory)
    evolution = _TerminalEvolution()

    grafo = criar_grafo(
        classificador=Classificador(),
        formatador=Formatador(),
        evolution=evolution,
        relogio=Relogio(settings.TIMEZONE_USUARIO),
        embedder=Embedder(),
        extrator=Extrator(llm=criar_llm()),
        repo_factory=repo_factory,
        checkpointer=MemorySaver(),
    )

    thread_id = f"terminal-{usuario_id}-{int(time.time())}"

    print("\n" + "─" * 50)
    print("  Agente Financeiro — modo terminal")
    print(f"  usuario_id={usuario_id} | Ctrl+C para sair")
    print("─" * 50 + "\n")

    try:
        while True:
            try:
                entrada = input("você: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAté logo!")
                break

            if not entrada:
                continue

            try:
                await grafo.ainvoke(
                    {
                        "messages": [HumanMessage(content=entrada)],
                        "usuario_id": usuario_id,
                        "numero": thread_id,
                    },
                    config={"configurable": {"thread_id": thread_id}},
                )
                if os.getenv("AGENT_DEBUG"):
                    snap = await grafo.aget_state({"configurable": {"thread_id": thread_id}})
                    v = snap.values
                    print(
                        f"[DEBUG] intencao={v.get('intencao', {}).get('acao')} "
                        f"acao_pendente={v.get('acao_pendente')} "
                        f"fase_pendente={v.get('fase_pendente')}",
                        flush=True,
                    )
            except Exception as exc:
                import traceback
                if os.getenv("AGENT_DEBUG"):
                    traceback.print_exc()
                print(f"\nagente: [erro interno: {exc}]\n")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Agente Financeiro — modo terminal")
    parser.add_argument("--usuario", type=int, default=1, help="ID do usuário (padrão: 1)")
    args = parser.parse_args()
    asyncio.run(_chat(args.usuario))


if __name__ == "__main__":
    main()
