# Plan: Dashboard Financeiro Flask

**Status:** APROVADO
**Feature:** dashboard-flask
**Spec:** specs/dashboard-flask/spec.md
**Exploração:** specs/dashboard-flask/exploracao.md

---

## Arquitetura

Dashboard Flask separado que reutiliza `app/` (models, repository, config) do agente.
Roda na porta 5000 com `uv run flask --app dashboard.app run --port 5000`.

### Estrutura de arquivos produzida

```
dashboard/
  __init__.py
  db.py               # engine + SessionFactory async (importa app.config)
  periodo.py          # resolver_periodo(str) → tuple[date, date]
  app.py              # Flask factory: registra blueprints + GET /
  blueprints/
    __init__.py
    api_resumo.py     # GET /api/resumo, GET /api/grafico/categorias
    api_graficos.py   # GET /api/grafico/mensal, GET /api/grafico/evolucao
    api_parcelas.py   # GET /api/parcelas-ativas, DELETE /api/grupos/<id>
    api_transacoes.py # GET/POST/PUT/DELETE /api/transacoes
  templates/
    base.html         # Bootstrap 5 + Chart.js via CDN, navbar, scripts
    index.html        # Layout completo: todos os widgets
  static/
    charts.js         # Inicializa Chart.js: pizza (RF-03), barras (RF-04), linha (RF-05)
    table.js          # Tabela paginada + modais CRUD (RF-07, RF-08)
    app.js            # Cards resumo (RF-02), parcelas (RF-06), seletor período (RF-01)
```

### Decisões técnicas

| # | Decisão | Alternativa descartada | Motivo |
|---|---------|----------------------|--------|
| 1 | `async def` routes com `flask[async]` | `asyncio.run()` por request | Mais limpo, sem custo de event loop |
| 2 | Blueprints por domínio | Tudo em `app.py` | Anti-colisão: tarefas paralelas não compartilham arquivo |
| 3 | Python slicing para paginação | DB LIMIT/OFFSET | MVP, dados pequenos (<1000 registros) |
| 4 | `listar_por_periodo` + filtro Python | Novo método no repo | Zero mudança no agente existente |
| 5 | `embedding=None` em inserção manual | Calcular embedding | Coluna já é nullable, sem OpenAI no dashboard |
| 6 | `periodo=tudo` → `date(2000,1,1)` | Sem piso | Consistente com o agente |
| 7 | JS em 3 arquivos (charts/table/app) | Um único dashboard.js | Anti-colisão entre T07/T08/T09 |
| 8 | `poolclass=NullPool` no engine | Pool padrão | Flask async cria 1 event loop por request; conexões asyncpg pooladas quebram entre loops |
| 9 | Pizza usa `listar_por_periodo` + agregação Python | `agregar_por_categoria` | O método do repo não filtra `tipo` — misturaria investimentos com gastos |
| 10 | `DELETE /api/grupos/<id>` só em `api_parcelas.py` | Duplicar em `api_transacoes.py` | Flask não permite registrar a mesma rota duas vezes |
| 11 | `create_app` registra blueprints via import dinâmico com `try/except ImportError`; cada módulo de blueprint expõe a variável `bp` | Imports estáticos em `app.py` | T01 precisa subir sozinho (lote 1) e T02-T05 rodam em paralelo sem que os outros blueprints existam no worktree |

---

## Tabela de Tarefas

| ID | Tarefa | Stack | Deps | Arquivos próprios |
|----|--------|-------|------|-------------------|
| 01 | Infraestrutura Flask (db, periodo, factory) | python | — | `dashboard/__init__.py`, `dashboard/db.py`, `dashboard/periodo.py`, `dashboard/app.py`, `dashboard/blueprints/__init__.py` |
| 02 | API Resumo e Categorias | python | 01 | `dashboard/blueprints/api_resumo.py` |
| 03 | API Gráficos Temporais | python | 01 | `dashboard/blueprints/api_graficos.py` |
| 04 | API Parcelas Ativas | python | 01 | `dashboard/blueprints/api_parcelas.py` |
| 05 | API CRUD Transações | python | 01 | `dashboard/blueprints/api_transacoes.py` |
| 06 | Templates HTML | python | 01 | `dashboard/templates/base.html`, `dashboard/templates/index.html` |
| 07 | JavaScript Gráficos (Chart.js) | python | 06 | `dashboard/static/charts.js` |
| 08 | JavaScript Tabela e CRUD | python | 06 | `dashboard/static/table.js` |
| 09 | JavaScript Cards e Parcelas | python | 06 | `dashboard/static/app.js` |

---

## DAG

```
         ┌──► T02 (api_resumo)
         ├──► T03 (api_graficos)
T01 ─────┼──► T04 (api_parcelas)
         ├──► T05 (api_transacoes)
         └──► T06 (templates) ──┬──► T07 (charts.js)
                                ├──► T08 (table.js)
                                └──► T09 (app.js)
```

- **Lote 1:** T01 (sequencial — foundation)
- **Lote 2:** T02, T03, T04, T05, T06 (paralelo — sem colisões)
- **Lote 3:** T07, T08, T09 (paralelo — sem colisões, após T06)

---

## Contratos

| Contrato | Arquivo | Status |
|----------|---------|--------|
| DB Session | `contracts/db-session.md` | Congelado |
| Período | `contracts/periodo.md` | Congelado |
| API JSON | `contracts/api-json.md` | Congelado |
| Repository Reuse | `contracts/repository-reuse.md` | Congelado |
| Interop JS | `contracts/js-interop.md` | Congelado |

---

## Ordem de integração

1. Merge T01 primeiro (sem deps)
2. Merge T02-T06 em qualquer ordem (branches independentes)
3. Merge T07-T09 em qualquer ordem (branches independentes)
4. Smoke test completo

---

## Riscos

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| `flask[async]` exige configuração extra | Baixa | T01 inclui endpoint `/health` para validar antes de T02-T06 |
| Agrupamento mensal em Python lento | Baixa | MVP aceitável; memoize se necessário |
| ~~`grupo_parcela_id` string vs UUID~~ | Resolvido | Verificado no código: `excluir_grupo` recebe `UUID` e converte com `str()` internamente; blueprints convertem `str → UUID` (T04) |
| ~~Event loop por request (asyncpg)~~ | Resolvido | `poolclass=NullPool` obrigatório no engine (decisão 8, contrato db-session) |

## Limitações conhecidas (aceitas no MVP)

- Editar transação pelo dashboard não recalcula o embedding — a busca semântica
  do agente usa o vetor antigo para esse registro (ver `contracts/repository-reuse.md`).
- `fim` dos períodos é `hoje`: parcelas com vencimento futuro dentro do mês atual
  não entram na tabela nem nos cards de resumo (aparecem só na seção RF-06).
  Mudar para "último dia do mês" é trivial em `dashboard/periodo.py` se desejado.

---

## Verificação da feature completa

```bash
# Instalar dependência nova
uv add flask[async]

# Rodar dashboard
uv run flask --app dashboard.app run --port 5000 --debug

# Abrir http://localhost:5000
# Testar manualmente todos os RF da spec
```

| RF | Check |
|----|-------|
| RF-01 | Mudar dropdown → todos os números/gráficos mudam |
| RF-02 | Cards somam valores conhecidos inseridos pelo agente |
| RF-03 | Pizza mostra só categorias com saldo; clicar filtra tabela |
| RF-04 | Barras mostram exatamente os últimos 6 meses |
| RF-05 | Linha tem 1 ponto por mês com dados |
| RF-06 | Parcela com data < hoje não aparece |
| RF-07 | Editar valor → SELECT no banco confirma atualização |
| RF-07 | Adicionar manual → aparece na tabela |
| RF-07 | Deletar → sumiu do banco |
| RF-08 | Seção investimentos só mostra `tipo=INVESTIMENTO` |
