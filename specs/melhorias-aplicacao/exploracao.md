# Exploração — melhorias-aplicacao

## Superfície atual (Flask monolítico)

Rotas em `dashboard/blueprints/`:

| Rota | Método | Arquivo |
|---|---|---|
| `/api/resumo` | GET | api_resumo.py |
| `/api/grafico/categorias` | GET | api_resumo.py |
| `/api/grafico/mensal` | GET | api_graficos.py |
| `/api/grafico/evolucao` | GET | api_graficos.py |
| `/api/parcelas-ativas` | GET | api_parcelas.py |
| `/api/grupos/<grupo>` | DELETE | api_parcelas.py |
| `/api/projecao` | GET | api_projecao.py |
| `/api/transacoes` | GET/POST | api_transacoes.py |
| `/api/transacoes/<id>` | PUT/DELETE | api_transacoes.py |
| `/` , `/health` | GET | app.py |

Frontend: `templates/base.html` + `index.html`; `static/{app,charts,table}.js`. O browser faz
`fetch` **same-origin** de `/api/*` (ver `app.js`, `charts.js`, `table.js`). Bootstrap 5 +
Chart.js via CDN. Container atual: `.container-fluid` (100% de largura).

## Acesso a dados

`dashboard/db.py` → `_SessionPorRequest`: cria engine + `NullPool` por request e descarta
(causa da lentidão). Os blueprints usam `app.repositories.transacao_repository.TransacaoRepository`
(async, SQLAlchemy 2.0) e `app.repositories.dtos`. Math em `Decimal`.

## Reuso (decisão aprovada)

- Backend FastAPI **reaproveita** `app/models`, `app/repositories` e `app/repositories/dtos`.
- Engine async **pooled** criado uma vez no lifespan do FastAPI (uvicorn = loop único persistente
  → pool reusado, sem o problema de loop-por-request do Flask).

## Convenções reais

- `uv` para tudo; `pytest` + `pytest-asyncio` (asyncio_mode=auto). **Não há ruff/mypy** no repo.
- Sem comentários no código (CLAUDE.md). `logging`, nunca `print`.
- Migrations Alembic em `migrations/` (head atual 0005). Schema não muda nesta feature.
- App do agente (`app/entrypoint`, pipeline) é independente do dashboard — não tocar.

## Riscos / atenção

- **Roteamento same-origin:** o JS busca `/api/*`. Mover a lógica p/ `:8000` exige que o frontend
  exponha `/api/*` como **proxy** (httpx → backend), senão quebra CORS e o JS. Decisão de arquitetura.
- **Testes existentes `tests/test_dashboard_*`** miram o Flask atual; ao remover `dashboard/`, eles
  saem/portam. Backend e frontend novos trazem seus próprios testes.
- **Janela 13 meses (RF-05):** hoje `mensal` usa 6 meses e `evolucao` consulta desde 2000 só meses
  com dados; ambos passam a −6..+6 e incluir futuro (parcelas/receitas já registradas).
- **Projeção (aprovado):** soma **todas** as transações do mês (não só PENDENTE).
- **start.py:** dois processos uvicorn/flask; encerramento limpo no CTRL+C (sinais no Windows).
