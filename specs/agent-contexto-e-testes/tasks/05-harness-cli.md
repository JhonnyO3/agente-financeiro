# Tarefa 05 — Harness CLI multi-turno (`scripts/chat_terminal.py`)

**Stack:** python  
**Estado:** todo  
**Depende de:** nenhuma (pode rodar com pipeline existente; 01/03/04 melhoram a qualidade)  
**Bloqueia:** 06

## Objetivo

Criar `scripts/chat_terminal.py` com modo interativo e modo batch. Ver contrato `contracts/harness.md` para spec completa.

## Arquivos que esta tarefa possui

- `scripts/chat_terminal.py` ← criar

## NÃO toca em

- `agent/` (nenhum arquivo de produção)
- `scripts/cenarios_teste.jsonl` (tarefa 06)

## Implementação (esqueleto)

```python
#!/usr/bin/env python3
"""Harness CLI multi-turno para testar o pipeline sem WhatsApp."""
import argparse, asyncio, json, sys, os
from datetime import datetime, timezone
from pathlib import Path

# Setup de env antes de importar o agent
os.environ.setdefault("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", "test"))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_API_KEY", "test")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")

from agent.domain.intencao import ItemCadastro, ParamsCadastrar
from agent.services.estado_store import EstadoStoreMemoria
from agent.services.classificador import Classificador
from agent.services.extrator import Extrator
from agent.services.formatador import Formatador
from agent.services.roteador import Roteador
from agent.tools.cadastrar import ToolCadastrar
from agent.tools.listar import ToolListar
from agent.tools.atualizar import ToolAtualizar
from agent.tools.excluir import ToolExcluir
from agent.tools.conversar import ToolConversar
from agent.services.relogio import Relogio
from agent.agents_llm import criar_llm


class RepoMock:
    """Repositório que não persiste — apenas aceita chamadas sem erro."""
    async def criar_lote(self, registros, usuario_id=None): pass
    async def listar(self, **kw): return []
    async def buscar_semantico(self, *a, **kw): return []
    async def atualizar(self, *a, **kw): pass
    async def excluir(self, *a, **kw): pass
    async def excluir_grupo(self, *a, **kw): pass
    async def excluir_por_filtros(self, **kw): pass
    async def buscar_por_referencia(self, *a, **kw): return []
    async def buscar_multiplos_candidatos(self, *a, **kw): return []


class HarnessAgente:
    def __init__(self, seed_path: str | None = None):
        self._estado_store = EstadoStoreMemoria()
        llm = self._criar_llm(seed_path)
        relogio = Relogio()
        repo = RepoMock()

        self._classificador = Classificador()
        self._extrator = Extrator(llm=llm)
        self._formatador = Formatador(llm=criar_llm(0.3))

        tool_cadastrar = ToolCadastrar(relogio=relogio, repository=repo)
        tool_listar = ToolListar(repository=repo, relogio=relogio)
        tool_atualizar = ToolAtualizar(repository=repo)
        tool_excluir = ToolExcluir(repository=repo)
        tool_conversar = ToolConversar(llm=llm)

        self._roteador = Roteador(
            tool_cadastrar=tool_cadastrar,
            tool_listar=tool_listar,
            tool_atualizar=tool_atualizar,
            tool_excluir=tool_excluir,
            tool_conversar=tool_conversar,
            estado_store=self._estado_store,
            repository=repo,
            extrator=self._extrator,
        )

    def _criar_llm(self, seed_path: str | None):
        if seed_path:
            return _SeedLLM(seed_path)
        return criar_llm()

    async def enviar(self, usuario_id: int, texto: str) -> str:
        from agent.domain.estado import Mensagem
        from agent.services.estado_store import resumir_pendencia
        agora = datetime.now(timezone.utc)

        estado = await self._estado_store.obter(usuario_id, agora)
        msg = Mensagem(papel="usuario", texto=texto, em=agora)
        await self._estado_store.registrar_mensagem(usuario_id, msg, agora)

        intencao = await self._classificador.classificar(
            mensagem=texto,
            historico=[f"{m.papel}: {m.texto}" for m in estado.historico],
            estado_pendente=resumir_pendencia(estado),
        )
        resultado = await self._roteador.rotear(intencao, usuario_id, agora, {"mensagem": texto})
        resposta = self._formatador.formatar(resultado)

        msg_r = Mensagem(papel="assistente", texto=resposta, em=agora)
        await self._estado_store.registrar_mensagem(usuario_id, msg_r, agora)
        return resposta

    async def resetar(self, usuario_id: int) -> None:
        from agent.domain.estado import EstadoConversa
        from datetime import datetime, timezone
        estado_vazio = EstadoConversa(usuario_id=usuario_id)
        await self._estado_store.salvar(estado_vazio)


async def modo_interativo(harness: HarnessAgente, usuario_id: int):
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
    with open(arquivo, encoding="utf-8") as f:
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
                detalhe = f"(contém '{espera}')" if espera and passou else \
                          f"(esperava '{espera}', recebeu: {resposta[:80]!r})" if espera else ""
                print(f"[Cenário {num_cenario} T{turno.get('turno',1)}] {msg[:50]} → {status} {detalhe}")
                if passou:
                    ok += 1
            except Exception as exc:
                print(f"[Cenário {num_cenario} T{turno.get('turno',1)}] {msg[:50]} → [ERRO] {exc}")

    print(f"\nResultado: {ok}/{total} passaram | {total - ok} falharam")
    return ok == total


def main():
    parser = argparse.ArgumentParser(description="Harness CLI do agente financeiro")
    parser.add_argument("--batch", metavar="ARQUIVO", help="Arquivo JSONL de cenários")
    parser.add_argument("--seed", metavar="ARQUIVO", help="JSON com respostas LLM mockadas")
    parser.add_argument("--usuario", type=int, default=1, help="ID do usuário (padrão: 1)")
    args = parser.parse_args()

    harness = HarnessAgente(seed_path=args.seed)

    if args.batch:
        passou = asyncio.run(modo_batch(harness, args.batch, args.usuario))
        sys.exit(0 if passou else 1)
    else:
        asyncio.run(modo_interativo(harness, args.usuario))


if __name__ == "__main__":
    main()
```

## Classe `_SeedLLM` (modo --seed)

```python
class _SeedLLM:
    """Substituto de ChatOpenAI que retorna respostas pré-gravadas."""
    def __init__(self, seed_path: str):
        with open(seed_path, encoding="utf-8") as f:
            data = json.load(f)
        self._respostas = data.get("respostas", [])
        self._fila: list[dict] = list(self._respostas)

    def with_structured_output(self, schema):
        return _SeedChain(self._fila, schema)


class _SeedChain:
    def __init__(self, fila, schema):
        self._fila = fila
        self._schema = schema

    async def ainvoke(self, prompt: str):
        for item in self._fila:
            if item.get("prompt_contém", "") in prompt:
                return self._schema.model_validate(item["resposta"])
        raise ValueError(f"Sem resposta seed para prompt: {prompt[:100]!r}")
```

## Critério de verificação local

```bash
uv run python scripts/chat_terminal.py --help
# deve imprimir help sem ImportError

echo '{"cenario":1,"turno":1,"msg":"ola","espera":null}' > /tmp/teste.jsonl
uv run python scripts/chat_terminal.py --batch /tmp/teste.jsonl
# deve terminar com código 0
```
