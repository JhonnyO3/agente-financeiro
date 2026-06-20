#!/usr/bin/env python3
"""Harness CLI multi-turno para testar o pipeline sem WhatsApp."""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Setup de env antes de importar o agent (config.py valida env vars ao importar)
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "sk-placeholder"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_API_KEY", "placeholder")
os.environ.setdefault("EVOLUTION_INSTANCE", "placeholder")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "harness@localhost")
os.environ.setdefault("RESPONSAVEL_PADRAO", "usuario")
os.environ.setdefault("WEBHOOK_APIKEY", "placeholder")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from agent.domain.estado import EstadoConversa, Mensagem
from agent.services.estado_store import EstadoStoreMemoria, resumir_pendencia
from agent.services.classificador import Classificador
from agent.services.formatador import Formatador
from agent.services.roteador import Roteador
from agent.tools.cadastrar import ToolCadastrar
from agent.tools.listar import ToolListar
from agent.tools.atualizar import ToolAtualizar
from agent.tools.excluir import ToolExcluir
from agent.tools.conversar import ToolConversar
from agent.services.relogio import Relogio
from agent.config import settings

# Importação condicional do Extrator (criado pela tarefa 01)
try:
    from agent.services.extrator import Extrator
    _TEM_EXTRATOR = True
except ImportError:
    _TEM_EXTRATOR = False


class RepoMock:
    """Repositório que não persiste — apenas aceita chamadas sem erro."""

    async def criar_lote(self, registros, usuario_id=None):
        pass

    async def listar(self, **kw):
        return []

    async def listar_por_periodo(self, inicio, fim):
        return []

    async def buscar_semantico(self, *a, **kw):
        return []

    async def atualizar(self, *a, **kw):
        pass

    async def excluir(self, *a, **kw):
        pass

    async def excluir_grupo(self, *a, **kw):
        pass

    async def excluir_por_filtros(self, **kw):
        pass

    async def buscar_por_referencia(self, *a, **kw):
        return []

    async def buscar_multiplos_candidatos(self, *a, **kw):
        return []

    async def contar_por_periodo_e_categoria(self, **kw):
        return 0

    async def buscar_parcelas_futuras_grupo(self, *a, **kw):
        return []


class _RagMock:
    """Mock de RAG que sempre retorna PISO (não encontrado)."""

    async def buscar(self, referencia, usuario_id):
        from agent.services.rag import ResultadoBusca, Faixa
        return ResultadoBusca(faixa=Faixa.PISO, candidatos=[])


class _SeedLLM:
    """Substituto de ChatOpenAI que retorna respostas pré-gravadas."""

    def __init__(self, seed_path: str):
        with open(seed_path, encoding="utf-8-sig") as f:
            data = json.load(f)
        self._respostas: list[dict] = data.get("respostas", [])

    def with_structured_output(self, schema):
        return _SeedChain(self._respostas, schema)

    async def ainvoke(self, prompt: str):
        """Suporte a chamada direta (sem structured output)."""
        for item in self._respostas:
            if item.get("prompt_contém", "") in str(prompt):
                resposta = item["resposta"]
                # Retorna objeto simples com .content se a resposta for string
                if isinstance(resposta, str):
                    return type("Resp", (), {"content": resposta})()
                return resposta
        # Fallback: resposta genérica
        return type("Resp", (), {"content": "Olá! Como posso ajudar?"})()


class _SeedChain:
    def __init__(self, respostas: list[dict], schema):
        self._respostas = respostas
        self._schema = schema

    async def ainvoke(self, prompt: str):
        prompt_str = str(prompt) if not isinstance(prompt, str) else prompt
        for item in self._respostas:
            if item.get("prompt_contém", "") in prompt_str:
                return self._schema.model_validate(item["resposta"])
        raise ValueError(
            f"Sem resposta seed para prompt iniciado por: {prompt_str[:80]!r}"
        )


class HarnessAgente:
    def __init__(self, seed_path: str | None = None):
        self._estado_store = EstadoStoreMemoria(
            max_historico=settings.HISTORICO_MAX_MENSAGENS,
            ttl_historico_horas=settings.HISTORICO_TTL_HORAS,
        )

        relogio = Relogio(tz=settings.TIMEZONE_USUARIO)
        repo = RepoMock()
        rag = _RagMock()

        # Se seed_path fornecido, injeta LLM mockado no módulo agents_llm
        if seed_path:
            self._injetar_seed_llm(seed_path)

        self._classificador = Classificador()
        self._formatador = Formatador()

        tool_cadastrar = ToolCadastrar(relogio=relogio, repository=repo)
        # ToolListar usa parâmetros: repo, relogio, usuario_id
        tool_listar = ToolListar(repo=repo, relogio=relogio, usuario_id=1)
        # ToolAtualizar e ToolExcluir usam rag
        tool_atualizar = ToolAtualizar(rag=rag, repository=repo, relogio=relogio)
        tool_excluir = ToolExcluir(rag=rag, repository=repo, relogio=relogio)
        # ToolConversar não aceita llm — cria internamente
        tool_conversar = ToolConversar()

        self._roteador = Roteador(
            tool_cadastrar=tool_cadastrar,
            tool_listar=tool_listar,
            tool_atualizar=tool_atualizar,
            tool_excluir=tool_excluir,
            tool_conversar=tool_conversar,
            estado_store=self._estado_store,
            repository=repo,
        )

    def _injetar_seed_llm(self, seed_path: str) -> None:
        """Substitui ChatOpenAI no módulo agents_llm por _SeedLLM."""
        import agent.agents_llm as _agents_llm

        seed_llm_instance = _SeedLLM(seed_path)

        # Monkey-patch: sobrescreve ChatOpenAI no namespace do módulo
        class _FakeChatOpenAI:
            def __new__(cls, *args, **kwargs):
                return seed_llm_instance

        _agents_llm.__dict__["ChatOpenAI"] = _FakeChatOpenAI

    async def enviar(self, usuario_id: int, texto: str) -> str:
        agora = datetime.now(timezone.utc)

        estado = await self._estado_store.obter(usuario_id, agora)
        msg = Mensagem(papel="usuario", texto=texto, em=agora)
        await self._estado_store.registrar_mensagem(usuario_id, msg, agora)

        intencao = await self._classificador.classificar(
            mensagem=texto,
            historico=[f"{m.papel}: {m.texto}" for m in estado.historico],
            estado_pendente=resumir_pendencia(estado),
        )

        resultado = await self._roteador.rotear(
            intencao, usuario_id, agora, {"mensagem": texto}
        )
        resposta = self._formatador.formatar(resultado)

        msg_r = Mensagem(papel="assistente", texto=resposta, em=agora)
        await self._estado_store.registrar_mensagem(usuario_id, msg_r, agora)
        return resposta

    async def resetar(self, usuario_id: int) -> None:
        estado_vazio = EstadoConversa(usuario_id=usuario_id)
        await self._estado_store.salvar(estado_vazio)


# ---------------------------------------------------------------------------
# Modos de execução
# ---------------------------------------------------------------------------


async def modo_interativo(harness: HarnessAgente, usuario_id: int) -> None:
    print("Harness interativo. Ctrl+C para sair.")
    while True:
        try:
            texto = input("você: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not texto:
            continue
        resposta = await harness.enviar(usuario_id, texto)
        print(f"agente: {resposta}\n")


async def modo_batch(harness: HarnessAgente, arquivo: str, usuario_id: int) -> bool:
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
        await harness.resetar(usuario_id)
        for turno in sorted(cenarios[num_cenario], key=lambda x: x.get("turno", 0)):
            total += 1
            msg = turno["msg"]
            espera = turno.get("espera")
            try:
                resposta = await harness.enviar(usuario_id, msg)
                passou = espera is None or espera.lower() in resposta.lower()
                status = "[OK]" if passou else "[FALHOU]"
                if espera and passou:
                    detalhe = f"(contém '{espera}')"
                elif espera:
                    detalhe = f"(esperava '{espera}', recebeu: {resposta[:80]!r})"
                else:
                    detalhe = ""
                print(
                    f"[Cenario {num_cenario} T{turno.get('turno', 1)}] "
                    f"{msg[:50]} -> {status} {detalhe}"
                )
                if passou:
                    ok += 1
            except Exception as exc:
                print(
                    f"[Cenario {num_cenario} T{turno.get('turno', 1)}] "
                    f"{msg[:50]} -> [ERRO] {exc}"
                )

    print(f"\nResultado: {ok}/{total} passaram | {total - ok} falharam")
    return ok == total


def main() -> None:
    parser = argparse.ArgumentParser(description="Harness CLI do agente financeiro")
    parser.add_argument("--batch", metavar="ARQUIVO", help="Arquivo JSONL de cenários")
    parser.add_argument(
        "--seed", metavar="ARQUIVO", help="JSON com respostas LLM mockadas"
    )
    parser.add_argument(
        "--usuario", type=int, default=1, help="ID do usuário (padrão: 1)"
    )
    args = parser.parse_args()

    harness = HarnessAgente(seed_path=args.seed)

    if args.batch:
        passou = asyncio.run(modo_batch(harness, args.batch, args.usuario))
        sys.exit(0 if passou else 1)
    else:
        asyncio.run(modo_interativo(harness, args.usuario))


if __name__ == "__main__":
    main()
