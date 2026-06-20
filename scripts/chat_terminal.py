#!/usr/bin/env python3
"""Harness CLI multi-turno para testar o pipeline sem WhatsApp.

Uso:
    uv run python scripts/chat_terminal.py                          # interativo
    uv run python scripts/chat_terminal.py --batch tests/agent/cenarios.jsonl
    uv run python scripts/chat_terminal.py --usuario 2
"""

import argparse
import asyncio
import json
import os
import sys
from types import SimpleNamespace

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Env mínimo antes de importar o agent
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "sk-placeholder"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_API_KEY", "placeholder")
os.environ.setdefault("EVOLUTION_INSTANCE", "placeholder")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "harness@localhost")
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
    """Repositório que não persiste — aceita todas as chamadas sem erro."""

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


def _criar_grafo():
    mock_evolution = AsyncMock()
    mock_evolution.enviar_mensagem = AsyncMock()

    repo = _RepoMock()
    repo_factory = lambda usuario_id: repo

    return criar_grafo(
        classificador=Classificador(),
        formatador=Formatador(),
        evolution=mock_evolution,
        relogio=Relogio(settings.TIMEZONE_USUARIO),
        embedder=Embedder(),
        extrator=Extrator(llm=criar_llm()),
        repo_factory=repo_factory,
        checkpointer=MemorySaver(),
    ), mock_evolution


async def _invocar(grafo, mock_evolution, usuario_id: int, thread_id: str, texto: str) -> str:
    mock_evolution.enviar_mensagem.reset_mock()
    await grafo.ainvoke(
        {
            "messages": [HumanMessage(content=texto)],
            "usuario_id": usuario_id,
            "numero": thread_id,
        },
        config={"configurable": {"thread_id": thread_id}},
    )
    calls = mock_evolution.enviar_mensagem.call_args_list
    return calls[-1][0][1] if calls else "(sem resposta)"


async def modo_interativo(grafo, mock_evolution, usuario_id: int) -> None:
    thread_id = f"terminal-{usuario_id}"
    print("Harness interativo. Ctrl+C para sair.")
    while True:
        try:
            texto = input("você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not texto:
            continue
        resposta = await _invocar(grafo, mock_evolution, usuario_id, thread_id, texto)
        print(f"agente: {resposta}\n")


async def modo_batch(grafo, mock_evolution, arquivo: str, usuario_id: int) -> bool:
    cenarios: dict[int, list[dict]] = {}
    with open(arquivo, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            c = obj.get("cenario", 1)
            cenarios.setdefault(c, []).append(obj)

    total = 0
    ok = 0
    for num_cenario in sorted(cenarios):
        thread_id = f"batch-{usuario_id}-{num_cenario}"
        for turno in sorted(cenarios[num_cenario], key=lambda x: x.get("turno", 0)):
            total += 1
            msg = turno["msg"]
            espera = turno.get("espera")
            try:
                resposta = await _invocar(grafo, mock_evolution, usuario_id, thread_id, msg)
                passou = espera is None or espera.lower() in resposta.lower()
                status = "[OK]" if passou else "[FALHOU]"
                detalhe = f"(contém '{espera}')" if espera and passou else (
                    f"(esperava '{espera}', recebeu: {resposta[:80]!r})" if espera else ""
                )
                print(f"[C{num_cenario} T{turno.get('turno', 1)}] {msg[:50]!r} → {status} {detalhe}")
                if passou:
                    ok += 1
            except Exception as exc:
                print(f"[C{num_cenario} T{turno.get('turno', 1)}] {msg[:50]!r} → [ERRO] {exc}")

    print(f"\nResultado: {ok}/{total} passaram | {total - ok} falharam")
    return ok == total


def main() -> None:
    parser = argparse.ArgumentParser(description="Harness CLI do agente financeiro")
    parser.add_argument("--batch", metavar="ARQUIVO", help="Arquivo JSONL de cenários")
    parser.add_argument("--usuario", type=int, default=1, help="ID do usuário (padrão: 1)")
    args = parser.parse_args()

    grafo, mock_evolution = _criar_grafo()

    if args.batch:
        passou = asyncio.run(modo_batch(grafo, mock_evolution, args.batch, args.usuario))
        sys.exit(0 if passou else 1)
    else:
        asyncio.run(modo_interativo(grafo, mock_evolution, args.usuario))


if __name__ == "__main__":
    main()
