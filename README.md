# Agente Financeiro via WhatsApp

Agente de IA pessoal acessível via WhatsApp para registrar, alterar, excluir e consultar gastos e investimentos. Todos os cálculos financeiros são feitos em Python — nunca pelo LLM.

## Funcionalidades

- **Cadastrar** gastos e investimentos em linguagem natural
- **Parcelamento** — cria N registros vinculados por `grupo_parcela_id`; pergunta automaticamente quando "cartão" é mencionado sem número de parcelas
- **Alterar e excluir** via busca semântica (pgvector) com confirmação explícita
- **Consultar** resumos mensais, semanais, gerais e status de parcelas por grupo
- **Painel web** (Flask) para visualizar gráficos e gerenciar transações — ver [Dashboard web](#dashboard-web-painel)
- Mensagens de outros números são descartadas silenciosamente

## Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12+ · `uv` |
| API | FastAPI · Evolution API (webhook) |
| IA | LangChain · `gpt-4o-mini` (classificação) · `gpt-4o` (resposta) · `text-embedding-3-small` |
| Banco | PostgreSQL + pgvector |
| Migrações | Alembic |
| Painel web | Flask (async) · Jinja2 · Chart.js · Bootstrap 5 (CDN) |

## Configuração

Crie um arquivo `.env` na raiz:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agente_financeiro
OPENAI_API_KEY=sk-...
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_INSTANCE=minha-instancia
EVOLUTION_API_KEY=sua-chave
WHATSAPP_ALLOWED_NUMBER=5511912345678
```

## Instalação e execução

```bash
# Instalar dependências
uv sync

# Subir o banco
docker compose up -d

# Aplicar migrations
uv run alembic upgrade head

# Iniciar o servidor
uv run uvicorn app.entrypoint.main:app --reload
```

Configure o webhook da Evolution API apontando para `POST /webhook/mensagem`.

## Dashboard web (painel)

Painel Flask para **visualizar e gerenciar** os dados registrados pelo agente — gráficos, resumos e CRUD de transações. Roda em processo separado e compartilha o mesmo banco e o mesmo `.env` do agente.

O painel é dividido em dois processos: um **backend** FastAPI (`backend.main:app`, porta 8000) que fala com o banco e expõe `/api/*`, e um **frontend** Flask (`frontend.app`, porta 5000) que serve as páginas e faz proxy de `/api/*` para o backend.

```bash
# A dependência flask[async] já vem no uv.lock — basta sincronizar
uv sync

# Subir backend e frontend juntos (logs prefixados, CTRL+C encerra ambos)
uv run python start.py

# Abra no navegador
http://localhost:5000
```

Para rodar cada processo isoladamente:

```bash
# Backend (porta 8000)
uv run uvicorn backend.main:app --port 8000

# Frontend (porta 5000)
uv run flask --app frontend.app run --port 5000
```

> O agente (FastAPI do webhook), o backend do painel (porta 8000) e o frontend (porta 5000) leem a mesma `DATABASE_URL`. O frontend depende do backend para os dados de `/api/*`.

### O que o painel oferece

| Recurso | Descrição |
|---|---|
| **Seletor de período** | Mês atual, mês anterior, últimos 3/6 meses, ano atual ou tudo — filtra todos os widgets |
| **Cards de resumo** | Total de gastos, total de investimentos e saldo (verde/vermelho conforme o sinal) |
| **Gráfico de pizza** | Gastos por categoria no período; clicar numa fatia filtra a tabela |
| **Barras mensais** | Gastos dos últimos 6 meses, empilhados por categoria |
| **Linha de evolução** | Gastos × investimentos ao longo de todos os meses com dados |
| **Parcelas em andamento** | Cards com barra de progresso; botão para excluir o grupo inteiro |
| **Tabela de transações** | Paginada (25/página), com filtros de tipo e categoria, edição e inclusão manual via modal e remoção |
| **Seção de investimentos** | Tabela e totais (período + histórico) apenas de `tipo = INVESTIMENTO` |

Todos os cálculos monetários são feitos em Python com `Decimal` e trafegam como string — o JavaScript apenas formata para exibição, nunca soma valores. Inclusões manuais gravam `embedding = NULL` (sem chamada à OpenAI no painel).

> **Sem autenticação** — o painel foi pensado para uso local/intranet. Não exponha a porta 5000 à internet sem uma camada de proteção própria.

### Endpoints da API do painel

Todos retornam JSON e aceitam `?periodo=`; `/api/transacoes` aceita também `tipo`, `categoria` e `pagina`.

| Método | Rota | Função |
|---|---|---|
| GET | `/` | Página principal (HTML) |
| GET | `/health` | Healthcheck `{"ok": true}` |
| GET | `/api/resumo` | Totais para os cards |
| GET | `/api/grafico/categorias` | Dados da pizza |
| GET | `/api/grafico/mensal` | Barras dos últimos 6 meses |
| GET | `/api/grafico/evolucao` | Linha de evolução |
| GET | `/api/parcelas-ativas` | Grupos com parcela futura |
| GET/POST | `/api/transacoes` | Listar (paginado) / criar manual |
| PUT/DELETE | `/api/transacoes/<id>` | Editar / excluir transação |
| DELETE | `/api/grupos/<grupo_parcela_id>` | Excluir um grupo de parcelas inteiro |

## Testes

```bash
uv run pytest tests/ -v

# Teste único
uv run pytest tests/test_pipeline.py::test_sem_estado_classificador_chamado -v
```

## Arquitetura

```
WhatsApp → Evolution API webhook
    → FastAPI (filtro por número autorizado)
    → debounce 10s (acumula mensagens por número)
    → Pipeline (máquina de estados + classificador de intenção)
    → Services: Cadastrar / Alterar / Excluir / Consultar
    → TransacaoRepository (SQLAlchemy 2.0 async + pgvector)
    → PostgreSQL
    → Formatador (gpt-4o formata a resposta)
    → Evolution API (envia resposta ao WhatsApp)
```

Os prompts ficam em `prompts/` — um arquivo por responsabilidade — para facilitar refinamento independente do código.

## Exemplos de uso

```
Usuário: gastei 45 reais no mercado hoje
Agente:  ✅ Registrado!
         📅 09/06/2026  💰 R$ 45,00  🏷️ ALIMENTACAO

Usuário: comprei celular samsung 6x de 150
Agente:  ✅ Registrado em 6x!
         💰 6x de R$ 150,00 (total R$ 900,00)
         📅 Parcelas: jun/26 · jul/26 · ago/26 · set/26 · out/26 · nov/26

Usuário: resumo de junho
Agente:  📊 Junho/2026 — Total gastos: R$ 945,00
         ALIMENTACAO: R$ 45,00  |  COMPRAS: R$ 900,00

Usuário: parcelas do celular
Agente:  Celular Samsung — 6x de R$ 150,00
         1/6 jun/26 ✅ Paga
         2/6 jul/26 🔜 Próxima
         3/6 ago/26 ⏳ Futura  ...
```
