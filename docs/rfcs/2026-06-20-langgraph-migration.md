# RFC: Migração para LangGraph

**Data:** 2026-06-20  
**Status:** Proposta (v2 — Strategy Pattern + nós autossuficientes)

---

## Motivação

A arquitetura atual implementa manualmente o que o LangGraph oferece de forma nativa:

| Hoje (manual) | LangGraph (nativo) |
|---|---|
| `EstadoConversa` + `EstadoStoreRedis` | `AgentState` + `RedisCheckpointer` |
| `Roteador` God Object com if/elif de ações | `StateGraph` com nós independentes |
| `acao_pendente` + `payload_pendente` gerenciados pelo Roteador | Estado persistido automaticamente por `thread_id` |
| `Worker` orquestrando 6 passos manualmente | Grafo declarativo com nós testáveis isoladamente |
| TTL implementado em `_limpar_expirados` | Nó de verificação no início do grafo |

O resultado é ~600 linhas de orquestração que podem ser substituídas por um grafo declarativo, mais simples de testar, estender e depurar.

---

## Decisão Arquitetural

### O que muda

- `Roteador` → `StateGraph` com operações autossuficientes (Strategy Pattern)
- `EstadoStore` (Redis) → `AsyncRedisSaver` (checkpointer nativo do LangGraph)
- `Worker` → `graph.ainvoke(input, config={"configurable": {"thread_id": usuario_id}})`
- `EstadoConversa` (Pydantic) → `AgentState` (TypedDict)
- `confirmar`, `selecionar`, `complementar` deixam de ser nós — viram **fases internas** de cada operação

### O que NÃO muda

- `Consumer` — debounce em Redis, asyncio task (apenas troca `worker.processar` por `graph.ainvoke`)
- Tools (`ToolCadastrar`, `ToolListar`, `ToolAtualizar`, `ToolExcluir`, `ToolConversar`) — lógica interna intacta
- `Classificador` e `Formatador` — lógica intacta, viram nós
- Prompts (`agent/prompts/*.md`) — sem alteração
- `BuscaRAG`, `Embedder`, `Relogio`, `Extrator` — sem alteração
- `domain/intencao.py`, `domain/resultado.py` — sem alteração
- `backend/` inteiro — sem alteração

---

## Princípio Central: Operações Autossuficientes

O problema do design original (e da v1 desta RFC) é que `confirmar`, `selecionar` e `complementar` existem como nós separados, o que recria o God Object do Roteador no grafo — agora o grafo precisa conhecer o ciclo de vida interno de cada operação.

**Decisão:** cada operação gerencia todas as suas próprias fases internamente via Strategy Pattern. O grafo apenas roteia para a operação correta; ela sabe o que fazer com base em `fase_pendente`.

O classificador continua classificando `confirmar`, `selecionar` e `complementar` normalmente — essa é sua responsabilidade. Mas o roteador não usa essas ações como destino: usa `acao_pendente` para devolver o controle à operação que estava aguardando.

---

## Arquitetura Proposta

### Estrutura de arquivos

```
agent/
  graph/
    __init__.py
    state.py       # AgentState TypedDict
    operacao.py    # Protocol Operacao (Strategy interface)
    operacoes/
      __init__.py
      cadastrar.py  # Cadastrar — gerencia _novo, _complementar, _confirmar
      listar.py     # Listar — sempre completa em um turno
      atualizar.py  # Atualizar — gerencia _novo, _selecionar, _confirmar
      excluir.py    # Excluir — gerencia _novo, _selecionar, _escopo, _confirmar
      conversar.py  # Conversar — sempre completa em um turno
    nodes.py       # Nós do grafo: thin wrappers sobre as operações + nós de infraestrutura
    edges.py       # Função de roteamento condicional
    builder.py     # Factory: build_graph(**deps) -> CompiledGraph

  entrypoint/
    consumer.py    # Atualizado: chama graph.ainvoke em vez de worker.processar
    main.py        # Atualizado: wiring do grafo, remove Worker

# Removidos:
  entrypoint/worker.py
  services/roteador.py
  services/estado_store.py
  domain/estado.py
```

### AgentState

```python
# agent/graph/state.py
from __future__ import annotations
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # LangGraph gerencia append automaticamente via add_messages
    messages: Annotated[list[BaseMessage], add_messages]

    # Contexto da mensagem atual (preenchido na entrada do Consumer)
    usuario_id: int
    numero: str

    # Output do nó classificar
    intencao: dict | None

    # Output do nó operação
    resultado: dict | None

    # Output do nó formatar — consumido pelo nó enviar
    resposta: str | None

    # Estado pendente — persiste entre turnos via checkpointer
    acao_pendente: str | None   # "cadastrar" | "atualizar" | "excluir"
    fase_pendente: str | None   # "aguardando_confirmacao" | "aguardando_selecao"
                                # | "aguardando_complemento" | "aguardando_escopo"
    payload_pendente: dict | None
    campos_faltantes: list[str]
    opcoes: list[dict] | None
    expira_em: str | None       # ISO 8601 UTC
```

`fase_pendente` substitui a inferência implícita de fase pelo status do resultado que existia no Roteador. O estado pendente é explícito e legível.

### Interface Strategy

```python
# agent/graph/operacao.py
from typing import Protocol
from agent.graph.state import AgentState


class Operacao(Protocol):
    async def executar(self, state: AgentState) -> dict: ...
```

Cada operação implementa este contrato. O nó no grafo é um thin wrapper que chama `operacao.executar(state)`.

### Topologia do Grafo

```
START
  └─→ verificar_expiracao        (zera campos de pendência expirados)
        └─→ classificar           (LLM: determina intenção)
              └─→ [rotear]        (aresta condicional — única)
                    ├─→ cadastrar  ─→ formatar ─→ enviar ─→ END
                    ├─→ listar     ─→ formatar ─→ enviar ─→ END
                    ├─→ atualizar  ─→ formatar ─→ enviar ─→ END
                    ├─→ excluir    ─→ formatar ─→ enviar ─→ END
                    ├─→ conversar  ─→ formatar ─→ enviar ─→ END
                    └─→ cancelar   ─→ formatar ─→ enviar ─→ END
```

**10 nós totais.** Sem `confirmar`, `selecionar`, `complementar` no grafo.

### Função de roteamento

```python
# agent/graph/edges.py
from agent.graph.state import AgentState

_ACOES_RESPOSTA = {"confirmar", "selecionar", "complementar"}


def rotear(state: AgentState) -> str:
    intencao = state.get("intencao") or {}
    acao = intencao.get("acao", "conversar")
    acao_pendente = state.get("acao_pendente")

    # Cancelamento explícito — nó compartilhado, limpa tudo
    if acao == "cancelar":
        return "cancelar"

    # Resposta a uma operação pendente — devolve para ela
    # A operação lê fase_pendente para saber o que fazer
    if acao_pendente and acao in _ACOES_RESPOSTA:
        return acao_pendente

    # Nova intenção operacional
    # Se havia pendência, a operação de destino a limpa antes de executar
    return acao
```

O roteador tem uma única responsabilidade: decidir para qual operação ir. Não sabe nada sobre o ciclo de vida interno de cada uma.

### Fluxo interno de cada operação

#### Cadastrar

```python
# agent/graph/operacoes/cadastrar.py

_FASES = {"aguardando_confirmacao", "aguardando_complemento"}

class Cadastrar:
    def __init__(self, *, relogio, repo_factory, extrator): ...

    async def executar(self, state: AgentState) -> dict:
        fase = state.get("fase_pendente")
        match fase:
            case "aguardando_confirmacao":  return await self._confirmar(state)
            case "aguardando_complemento":  return await self._complementar(state)
            case _:                         return await self._novo(state)

    async def _novo(self, state) -> dict:
        # Limpa pendência stale de outra operação se houver
        # Extrai itens da intencao, passa pelo extrator se necessário
        # ToolCadastrar.executar(itens, contexto)
        # Se campos_faltantes → salva fase="aguardando_complemento"
        # Se ok → salva fase="aguardando_confirmacao" com registros no payload

    async def _complementar(self, state) -> dict:
        # Lê ParamsComplementar da intencao
        # Preenche campo no payload_pendente, remove de campos_faltantes
        # Se ainda faltam campos → mantém fase="aguardando_complemento"
        # Se completo → salva fase="aguardando_confirmacao"

    async def _confirmar(self, state) -> dict:
        # repo.criar_lote(payload_pendente["registros"], usuario_id)
        # Limpa toda a pendência
        # Retorna status="concluido"
```

#### Listar

```python
# agent/graph/operacoes/listar.py

class Listar:
    def __init__(self, *, relogio, repo_factory): ...

    async def executar(self, state: AgentState) -> dict:
        # Limpa pendência stale se houver (listar nunca tem fases)
        # ToolListar.executar(params, contexto)
        # Sempre retorna concluido ou vazio — nunca salva pendência
```

#### Atualizar

```python
# agent/graph/operacoes/atualizar.py

class Atualizar:
    def __init__(self, *, relogio, repo_factory, embedder): ...

    async def executar(self, state: AgentState) -> dict:
        fase = state.get("fase_pendente")
        match fase:
            case "aguardando_selecao":      return await self._selecionar(state)
            case "aguardando_confirmacao":  return await self._confirmar(state)
            case _:                         return await self._novo(state)

    async def _novo(self, state) -> dict:
        # ToolAtualizar.executar(params, usuario_id) — usa RAG internamente
        # PISO → resultado nao_encontrado, sem pendência
        # AMBIGUO → salva fase="aguardando_selecao" + opcoes no state
        # MATCH → salva fase="aguardando_confirmacao" com diff no payload

    async def _selecionar(self, state) -> dict:
        # Lê ParamsSelecionar da intencao, resolve opcao das state["opcoes"]
        # Re-executa lógica de MATCH com a ref resolvida
        # Salva fase="aguardando_confirmacao"

    async def _confirmar(self, state) -> dict:
        # repo.atualizar(registro, diff, usuario_id)
        # Propaga para parcelas futuras se payload indicar
        # Limpa pendência, retorna concluido
```

#### Excluir

```python
# agent/graph/operacoes/excluir.py

class Excluir:
    def __init__(self, *, relogio, repo_factory, embedder): ...

    async def executar(self, state: AgentState) -> dict:
        fase = state.get("fase_pendente")
        match fase:
            case "aguardando_selecao":      return await self._selecionar(state)
            case "aguardando_escopo":       return await self._escopo(state)
            case "aguardando_confirmacao":  return await self._confirmar(state)
            case _:                         return await self._novo(state)

    async def _novo(self, state) -> dict:
        # Modo lote (sem referência, com período):
        #   conta registros → salva fase="aguardando_confirmacao" modo="lote"
        # Modo individual (com referência):
        #   RAG PISO → nao_encontrado, sem pendência
        #   RAG AMBIGUO → salva fase="aguardando_selecao" + opcoes
        #   RAG MATCH com parcelas futuras → salva fase="aguardando_escopo"
        #   RAG MATCH sem parcelas → salva fase="aguardando_confirmacao"

    async def _selecionar(self, state) -> dict:
        # Resolve opcao das state["opcoes"]
        # Verifica parcelas futuras na ref selecionada
        # → fase="aguardando_escopo" ou fase="aguardando_confirmacao"

    async def _escopo(self, state) -> dict:
        # Lê resposta do usuário (só esta parcela / todas as parcelas)
        # Define modo no payload_pendente
        # Salva fase="aguardando_confirmacao"

    async def _confirmar(self, state) -> dict:
        # Lê modo do payload: lote / grupo / individual
        # Executa a operação correta no repo
        # Limpa pendência, retorna concluido
```

#### Conversar

```python
# agent/graph/operacoes/conversar.py

class Conversar:
    def __init__(self): ...

    async def executar(self, state: AgentState) -> dict:
        # Limpa pendência stale se houver (conversar nunca tem fases)
        # ToolConversar.executar(mensagem, historico_do_state)
        # Sempre retorna concluido — nunca salva pendência
```

### Nós do grafo (thin wrappers)

```python
# agent/graph/nodes.py

class Nodes:
    def __init__(self, *, cadastrar, listar, atualizar, excluir, conversar,
                 classificador, formatador, evolution_client): ...

    # Infraestrutura
    async def verificar_expiracao(self, state: AgentState) -> dict:
        agora = datetime.now(timezone.utc)
        expira_em = state.get("expira_em")
        if expira_em and datetime.fromisoformat(expira_em) < agora:
            return {
                "acao_pendente": None, "fase_pendente": None,
                "payload_pendente": None, "campos_faltantes": [],
                "opcoes": None, "expira_em": None,
            }
        return {}

    async def classificar(self, state: AgentState) -> dict:
        historico = [f"{m.type}: {m.content}" for m in state["messages"][:-1]]
        estado_pendente = _resumir_pendencia(state)
        intencao = await self._classificador.classificar(
            mensagem=state["messages"][-1].content,
            historico=historico,
            estado_pendente=estado_pendente,
        )
        return {"intencao": intencao.model_dump()}

    async def cancelar(self, state: AgentState) -> dict:
        return {
            "resultado": ResultadoTool(acao="menu", status="concluido", dados={}).model_dump(),
            "acao_pendente": None, "fase_pendente": None,
            "payload_pendente": None, "campos_faltantes": [],
            "opcoes": None, "expira_em": None,
        }

    async def formatar(self, state: AgentState) -> dict:
        resultado = ResultadoTool(**state["resultado"])
        resposta = self._formatador.formatar(resultado)
        return {"messages": [AIMessage(content=resposta)], "resposta": resposta}

    async def enviar(self, state: AgentState) -> dict:
        await self._evolution.enviar_mensagem(state["numero"], state["resposta"])
        return {}

    # Operações — thin wrappers sobre as strategies
    async def cadastrar(self, state: AgentState) -> dict:
        return await self._cadastrar.executar(state)

    async def listar(self, state: AgentState) -> dict:
        return await self._listar.executar(state)

    async def atualizar(self, state: AgentState) -> dict:
        return await self._atualizar.executar(state)

    async def excluir(self, state: AgentState) -> dict:
        return await self._excluir.executar(state)

    async def conversar(self, state: AgentState) -> dict:
        return await self._conversar.executar(state)
```

### Factory do grafo

```python
# agent/graph/builder.py
from typing import TYPE_CHECKING
from langgraph.graph import StateGraph, END
from agent.graph.state import AgentState
from agent.graph.nodes import Nodes
from agent.graph.edges import rotear
from agent.graph.operacoes.cadastrar import Cadastrar
from agent.graph.operacoes.listar import Listar
from agent.graph.operacoes.atualizar import Atualizar
from agent.graph.operacoes.excluir import Excluir
from agent.graph.operacoes.conversar import Conversar

if TYPE_CHECKING:
    from agent.services.classificador import Classificador
    from agent.services.formatador import Formatador
    from agent.integrations.evolution_client import EvolutionApiClient
    from agent.agents_llm import Embedder, Extrator
    from agent.services.relogio import Relogio
    from backend.repositories.transacao_repository import TransacaoRepository
    from collections.abc import Callable


def build_graph(
    *,
    classificador: Classificador,
    formatador: Formatador,
    evolution_client: EvolutionApiClient,
    repo_factory: Callable[[int], TransacaoRepository],
    relogio: Relogio,
    embedder: Embedder,
    extrator: Extrator,
    checkpointer,
):
    nodes = Nodes(
        cadastrar=Cadastrar(relogio=relogio, repo_factory=repo_factory, extrator=extrator),
        listar=Listar(relogio=relogio, repo_factory=repo_factory),
        atualizar=Atualizar(relogio=relogio, repo_factory=repo_factory, embedder=embedder),
        excluir=Excluir(relogio=relogio, repo_factory=repo_factory, embedder=embedder),
        conversar=Conversar(),
        classificador=classificador,
        formatador=formatador,
        evolution_client=evolution_client,
    )

    g = StateGraph(AgentState)

    g.add_node("verificar_expiracao", nodes.verificar_expiracao)
    g.add_node("classificar", nodes.classificar)
    g.add_node("cadastrar", nodes.cadastrar)
    g.add_node("listar", nodes.listar)
    g.add_node("atualizar", nodes.atualizar)
    g.add_node("excluir", nodes.excluir)
    g.add_node("conversar", nodes.conversar)
    g.add_node("cancelar", nodes.cancelar)
    g.add_node("formatar", nodes.formatar)
    g.add_node("enviar", nodes.enviar)

    g.set_entry_point("verificar_expiracao")
    g.add_edge("verificar_expiracao", "classificar")
    g.add_conditional_edges("classificar", rotear, {
        "cadastrar":   "cadastrar",
        "listar":      "listar",
        "atualizar":   "atualizar",
        "excluir":     "excluir",
        "conversar":   "conversar",
        "cancelar":    "cancelar",
        "desconhecida": "conversar",
    })

    for node in ("cadastrar", "listar", "atualizar", "excluir", "conversar", "cancelar"):
        g.add_edge(node, "formatar")

    g.add_edge("formatar", "enviar")
    g.add_edge("enviar", END)

    return g.compile(checkpointer=checkpointer)
```

### Consumer atualizado

```python
# agent/entrypoint/consumer.py (trecho _disparar)

async def _disparar(self, usuario_id: int, numero: str) -> None:
    try:
        if self._debounce > 0:
            await asyncio.sleep(self._debounce)

        key = _BUFFER_KEY.format(numero=numero)
        fragmentos = await self._redis.lrange(key, 0, -1)
        await self._redis.delete(key)
        self._timers.pop(numero, None)

        if not fragmentos:
            return

        texto = "\n".join(fragmentos)

        await self._graph.ainvoke(
            {
                "messages": [HumanMessage(content=texto)],
                "usuario_id": usuario_id,
                "numero": numero,
            },
            config={"configurable": {"thread_id": str(usuario_id)}},
        )
    except asyncio.CancelledError:
        pass
```

O nó `enviar` cuida da Evolution API. O Consumer não precisa mais do `evolution_client`.

### main.py atualizado (trecho lifespan)

```python
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from agent.graph.builder import build_graph

checkpointer = AsyncRedisSaver.from_conn_string(settings.REDIS_URL)

graph = build_graph(
    classificador=classificador,
    formatador=formatador,
    evolution_client=evolution_client,
    repo_factory=repo_factory,
    relogio=relogio,
    embedder=embedder,
    extrator=extrator,
    checkpointer=checkpointer,
)

consumer = Consumer(
    fila=fila,
    graph=graph,
    redis_client=redis_client,
    debounce_segundos=settings.DEBOUNCE_SEGUNDOS,
)
```

---

## Sequência de Implementação

| # | Tarefa | Depende de | Entregável |
|---|---|---|---|
| 1 | Dependências e AgentState | — | `state.py`, `operacao.py`, `langgraph` instalado |
| 2 | Operações (Strategy) | 1 | `operacoes/cadastrar.py`, `listar.py`, `atualizar.py`, `excluir.py`, `conversar.py` + testes |
| 3 | Nós e Roteamento | 1, 2 | `nodes.py`, `edges.py` + testes de `rotear` |
| 4 | Factory e integração | 1, 2, 3 | `builder.py` + teste de integração multi-turno |
| 5 | Consumer e main.py | 4 | Consumer usando `graph.ainvoke`, lifespan atualizado |
| 6 | Remoção do legado | 5 | Worker, Roteador, EstadoStore deletados; suite verde |

---

## Lista de Tarefas de Implementação

### Tarefa 1 — Dependências e AgentState

**Objetivo:** instalar LangGraph e definir o contrato de estado.

- Adicionar ao `pyproject.toml`: `langgraph>=0.2`, `langgraph-checkpoint-redis>=0.0.6`
- Rodar `uv sync`
- Criar `agent/graph/__init__.py` e `agent/graph/operacoes/__init__.py`
- Criar `agent/graph/state.py` com `AgentState` conforme spec acima
- Criar `agent/graph/operacao.py` com o `Protocol Operacao`
- **Teste:** importar `AgentState`, verificar todos os campos; importar `Operacao`, verificar que é um Protocol

---

### Tarefa 2 — Operações (Strategy)

**Objetivo:** implementar as 5 operações em `agent/graph/operacoes/`.

Cada classe implementa `Operacao` e gerencia suas próprias fases via `match state.get("fase_pendente")`.

Regras comuns a todas:
- Criar repo via `self._repo_factory(state["usuario_id"])` dentro de cada método
- Salvar pendência: escrever `acao_pendente`, `fase_pendente`, `payload_pendente`, `expira_em` (agora + 5min ISO)
- Limpar pendência: zerar todos os campos acima + `campos_faltantes`, `opcoes`
- Operações sem fases (`Listar`, `Conversar`): sempre limpam pendência stale antes de executar

**Testes:** testar cada fase de cada operação isoladamente com `AgentState` mockado — sem grafo, sem LLM real, sem banco real.

---

### Tarefa 3 — Nós e Roteamento

**Objetivo:** implementar `agent/graph/nodes.py` e `agent/graph/edges.py`.

- `Nodes` como thin wrappers sobre as operações + nós de infraestrutura
- `rotear(state) -> str` conforme spec acima
- `_resumir_pendencia(state) -> str` — função auxiliar que gera descrição legível do estado pendente para o classificador (migra de `estado_store.resumir_pendencia`)

**Testes:** testar `rotear` com dicts cobrindo todos os casos: sem pendência, com pendência + acao de resposta, com pendência + nova acao operacional, cancelar.

---

### Tarefa 4 — Factory e integração

**Objetivo:** implementar `agent/graph/builder.py` e validar o grafo completo.

- `build_graph(**deps)` conforme spec acima
- **Teste de integração:** compilar com `MemorySaver`, invocar dois turnos em sequência com `thread_id` fixo, verificar que o state da segunda invocação contém o histórico da primeira (usando mocks para LLM e Evolution API)

---

### Tarefa 5 — Consumer e main.py

**Objetivo:** conectar o grafo ao ponto de entrada.

- `Consumer.__init__` recebe `graph` em vez de `worker`
- `Consumer._disparar` chama `graph.ainvoke` conforme spec acima
- `main.py`: remove `Worker`, adiciona checkpointer e `build_graph`
- **Teste:** smoke test end-to-end (webhook → fila → debounce → grafo → Evolution API mockada)

---

### Tarefa 6 — Remoção do código legado

**Objetivo:** deletar o que o grafo substituiu e garantir que a suite passa.

Arquivos a remover:
- `agent/entrypoint/worker.py`
- `agent/services/roteador.py`
- `agent/services/estado_store.py`
- `agent/domain/estado.py`

Testes a remover/substituir:
- `tests/test_worker.py` → remover (coberto pelos testes das operações)
- `tests/test_roteador.py` → remover (coberto pelos testes de `rotear` e integração)
- `tests/test_estado_store.py` → remover

Rodar `uv run pytest tests/ -v` e corrigir imports quebrados.

---

## Fluxo Final Esperado

```
WhatsApp → Evolution API webhook → FastAPI
  → Consumer (fila asyncio + buffer Redis + debounce 10s)
  → graph.ainvoke(
        {"messages": [HumanMessage(content=texto)], "usuario_id": ..., "numero": ...},
        config={"configurable": {"thread_id": str(usuario_id)}}
    )
      → verificar_expiracao   zera fase_pendente/acao_pendente se TTL expirou
      → classificar            LLM classifica intenção com histórico do State
      → [rotear]               decide: nova operação ou continua pendente?
      → <operacao>.executar()  lógica determinística, gerencia suas próprias fases
      → formatar               LLM formata resposta para WhatsApp
      → enviar                 Evolution API envia mensagem
  → State persistido automaticamente no Redis via RedisCheckpointer
    (próxima mensagem retoma com histórico e pendência intactos)
```

**Exemplo de fluxo multi-turno (excluir com parcelas):**

```
Turno 1 — Usuário: "apaga a conta do iFood"
  Excluir._novo()  → RAG encontra 1 transação com 3 parcelas futuras
                   → salva acao_pendente="excluir", fase_pendente="aguardando_escopo"
  Resposta: "Encontrei o iFood de R$45. Excluir só esta parcela ou todas as 4?"

Turno 2 — Usuário: "todas"
  rotear()         → acao="confirmar", acao_pendente="excluir" → roteia para "excluir"
  Excluir._escopo() → define modo="grupo" no payload
                    → salva fase_pendente="aguardando_confirmacao"
  Resposta: "Confirma a exclusão de 4 parcelas totalizando R$180?"

Turno 3 — Usuário: "sim"
  rotear()           → acao="confirmar", acao_pendente="excluir" → roteia para "excluir"
  Excluir._confirmar() → repo.excluir_grupo(grupo_parcela_id)
                       → limpa toda pendência
  Resposta: "Pronto! 4 parcelas do iFood excluídas."
```

---

## O que o desenvolvedor ganha

1. **Histórico gerenciado automaticamente** — `add_messages` acumula a conversa sem código manual
2. **Persistência zero-config** — trocar `MemorySaver` por `AsyncRedisSaver` é uma linha
3. **Operações isoladas e testáveis** — cada fase de cada operação é um método testável independentemente
4. **Extensibilidade** — nova operação = novo arquivo em `operacoes/` + uma aresta no builder
5. **Grafo simples** — 10 nós, 1 aresta condicional, sem ciclos, sem nós de controle
6. **~600 linhas eliminadas** — Worker, Roteador, EstadoStore desaparecem

---

## Riscos

| Risco | Mitigação |
|---|---|
| TTL por campo não é nativo no LangGraph | Nó `verificar_expiracao` no início do grafo, verifica `expira_em` ISO no State |
| `langgraph-checkpoint-redis` é pacote relativamente novo | Pinnar versão no `uv.lock`; toda a lógica de negócio funciona com `MemorySaver` em CI |
| `usuario_id` e `numero` precisam estar no State mas não são mensagens | São campos fixos do `AgentState`; o Consumer os injeta na primeira invocação, o checkpointer os persiste automaticamente nos turnos seguintes |
| Pendência stale quando nova intenção operacional chega | Cada operação limpa `acao_pendente`/`fase_pendente` no início de `_novo()` |
