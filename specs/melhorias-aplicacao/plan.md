# Plano Técnico — melhorias-aplicacao

**Status:** Aprovado
**Spec:** `specs/melhorias-aplicacao/spec.md` (Aprovada)
**Contratos:** `db-engine.md`, `api-endpoints.md`, `frontend-backend.md`, `projecao-13-meses.md` (todos Congelados)

## Arquitetura-alvo

```
backend/   FastAPI (:8000) — controllers/services/dtos/entities, engine pooled, reusa app/repositories
frontend/  Flask  (:5000) — blueprints (páginas + proxy /api/*), services httpx, templates, static
start.py   sobe os dois processos com logs prefixados e shutdown limpo
app/       agente WhatsApp — INALTERADO
dashboard/ REMOVIDO ao final (substituído por backend/ + frontend/)
```

Fluxo: browser → `/api/*` same-origin (Flask :5000, proxy) → httpx → FastAPI (:8000) →
service → `TransacaoRepository` (sessão do pool) → Postgres.

## Decisões

- **Pool no lifespan do FastAPI** resolve a lentidão (medido: 2.8s→0.4s). Sem `NullPool`.
- **Proxy same-origin** no frontend mantém o JS atual sem CORS nem reescrita de URLs.
- **Reuso de `app/repositories`** e `app/models` no backend (sem duplicar parcelas/embeddings).
- **Projeção = soma de todas as transações do mês** (não só PENDENTE), janela de 13 meses.
- **main.py do backend registra routers por lista fixa** (módulos ausentes são ignorados na subida),
  para que T02/T03 criem seus controllers sem colidir em `main.py`.
- **`dashboard/` e `tests/test_dashboard_*` são removidos** na tarefa final, após backend+frontend verdes.

## Tarefas (DAG)

| ID | Tarefa | Stack | Depende de | Arquivos (posse) |
|----|--------|-------|-----------|------------------|
| 01 | Backend core: app FastAPI, lifespan, engine pooled, config, deps, log de gargalo | python | contratos | `backend/__init__.py`, `backend/main.py`, `backend/config.py`, `backend/db.py`, `backend/dependencies.py`, `tests/backend/test_boot.py` |
| 02 | Backend transações + resumo + parcelas + categorias | python | 01 | `backend/controllers/{transacoes,resumo,parcelas}.py`, `backend/services/{transacoes,resumo,parcelas}.py`, `backend/dtos/{transacao,resumo}.py`, `tests/backend/test_transacoes.py`, `test_resumo.py`, `test_parcelas.py` |
| 03 | Backend gráficos + projeção (13 meses, receitas, todas as transações) | python | 01 | `backend/controllers/{graficos,projecao}.py`, `backend/services/{graficos,projecao}.py`, `backend/dtos/graficos.py`, `backend/services/janela.py`, `tests/backend/test_graficos.py`, `test_projecao.py` |
| 04 | Frontend em camadas: proxy `/api/*`, páginas, layout (max-1400/centro/borda/mobile), JS com linha de receitas | python | contratos | `frontend/**`, `tests/frontend/**` |
| 05 | `start.py` + remoção de `dashboard/` e testes antigos | python | 01,02,03,04 | `start.py`, (remove) `dashboard/**`, `tests/test_dashboard_*` |

DAG: `contratos → 01 → {02, 03}` ; `04` em paralelo (depende só dos contratos) ; `05` por último.

## Ordem de integração

1. T01 (backend sobe vazio, valida engine pooled + log).
2. T02 e T03 (controllers/services) — merge em qualquer ordem (arquivos distintos).
3. T04 (frontend) — pode mergear em paralelo; valida proxy contra os contratos.
4. T05 (start.py + remoção do dashboard antigo) por último.
5. Verificação total: `uv run pytest` + medição de tempo dos endpoints (<1s na 2ª chamada).

## Riscos

- **Shutdown no Windows (start.py):** propagar CTRL+C aos subprocessos (usar `CREATE_NEW_PROCESS_GROUP`/
  `terminate()` no Windows; `SIGINT` no POSIX). Testar encerramento sem órfãos.
- **Medição de performance depende de DB real** (não há Postgres no ambiente de teste); o critério
  <1s é verificado manualmente pelo usuário; testes usam repo mockado.
- **Remoção do `dashboard/` (T05)** só após backend+frontend cobrirem 100% das rotas — checar paridade.
- **Paridade de JSON:** o proxy e o front dependem do formato atual; `api-endpoints.md` é a verdade.

## Verificação da feature

- `uv run pytest` verde (novos testes backend/frontend; testes do agente intactos).
- `uv run python start.py` sobe os dois serviços; página carrega; CTRL+C encerra ambos.
- Endpoints respondem <1s na 2ª chamada (medição manual contra o DB real).
- Gráfico de evolução com 3 linhas; mensal/evolucao/projecao com 13 meses; layout centralizado/responsivo.
