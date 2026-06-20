# Migração LangGraph — Controle de Ondas

**RFC:** `docs/rfcs/2026-06-20-langgraph-migration.md`  
**Início:** 2026-06-20  
**Fase atual:** Implementação (sem testes — testes na próxima etapa)

---

## Ondas

### Onda 1 — Fundações ✅

| Tarefa | Arquivo(s) | Status | Branch/Worktree |
|---|---|---|---|
| T1 — AgentState + Protocol + deps | `agent/graph/state.py`, `agent/graph/operacao.py`, `pyproject.toml` | ✅ Concluído | mergeado em master (399a274) |

**Critério de conclusão:** `langgraph` instalável via `uv sync`, `AgentState` importável, `Operacao` Protocol definido.

---

### Onda 2 — Operações (paralela) ✅

| Tarefa | Arquivo(s) | Status | Branch/Worktree |
|---|---|---|---|
| T2a — Cadastrar | `agent/graph/operacoes/cadastrar.py` | ✅ Concluído | mergeado em master (de4a54b) |
| T2b — Listar | `agent/graph/operacoes/listar.py` | ✅ Concluído | mergeado em master (4abb8b4) |
| T2c — Atualizar | `agent/graph/operacoes/atualizar.py` | ✅ Concluído | mergeado em master (1538116) |
| T2d — Excluir | `agent/graph/operacoes/excluir.py` | ✅ Concluído | mergeado em master (e757c7c) |
| T2e — Conversar | `agent/graph/operacoes/conversar.py` | ✅ Concluído | mergeado em master (e88c096) |

**Critério de conclusão:** cada operação implementa `Operacao`, gerencia suas próprias fases via `match fase_pendente`.

---

### Onda 3 — Nós e Roteamento 🔄

> Onda 2 concluída — Onda 3 iniciando.

| Tarefa | Arquivo(s) | Status | Branch/Worktree |
|---|---|---|---|
| T3 — Nodes + Edges | `agent/graph/nodes.py`, `agent/graph/edges.py` | 🔄 Em andamento | — |

---

### Onda 4 — Factory do Grafo ⏳

> Inicia após merge da Onda 3.

| Tarefa | Arquivo(s) | Status | Branch/Worktree |
|---|---|---|---|
| T4 — Builder | `agent/graph/builder.py` | ⏳ A iniciar | — |

---

### Onda 5 — Entrypoint ⏳

> Inicia após merge da Onda 4.

| Tarefa | Arquivo(s) | Status | Branch/Worktree |
|---|---|---|---|
| T5 — Consumer + main.py | `agent/entrypoint/consumer.py`, `agent/entrypoint/main.py` | ⏳ A iniciar | — |

---

### Onda 6 — Remoção do Legado ⏳

> Inicia após merge da Onda 5.

| Tarefa | Arquivo(s) | Status | Branch/Worktree |
|---|---|---|---|
| T6 — Delete legado | `worker.py`, `roteador.py`, `estado_store.py`, `domain/estado.py` | ⏳ A iniciar | — |

---

## Legenda

| Símbolo | Significado |
|---|---|
| ⏳ | A iniciar |
| 🔄 | Em andamento |
| ✅ | Concluído e mergeado |
| ❌ | Bloqueado |

---

## Histórico de merges

| Onda | Branch | Merged em | Observações |
|---|---|---|---|
| 1 | worktree-agent-a6ccc4430855051ff | 399a274 | AgentState, Operacao Protocol, deps langgraph |
| 2a | worktree-agent-a3ca92b8ca4339dc8 | de4a54b | Cadastrar (3 fases) |
| 2b | worktree-agent-a76c3f5ed2164ed9a | 4abb8b4 | Listar (1 fase) |
| 2c | worktree-agent-acf061d36b7cc16ea | 1538116 | Atualizar (3 fases) |
| 2d | worktree-agent-ad010e6a345563838 | e757c7c | Excluir (4 fases) |
| 2e | worktree-agent-a9409d09259b44e47 | e88c096 | Conversar (1 fase) |
