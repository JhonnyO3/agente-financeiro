# Spec: Melhorias de Aplicação — Backend FastAPI, Frontend em camadas, Projeção e Layout

**Status:** Aprovado
**Feature:** melhorias-aplicacao
**Origem:** `specs/melhorias-aplicacao/negocio.md`

## Contexto

O dashboard atual é um módulo Flask monolítico que acessa o Postgres direto via um
`SessionFactory` que **cria um engine novo com `NullPool` a cada request** e o descarta no
fim (`dashboard/db.py`). Isso existe porque o Flask executa cada view async num event loop
novo (asgiref), e um engine async com pool compartilhado quebra entre loops
(commit `4a5baca`).

**Gargalo medido (local, contra o Postgres remoto `2.25.184.39`):**

| Padrão | Tempo por chamada |
|---|---|
| Atual: engine novo + `NullPool` por request | **~2.8s** (handshake TCP+TLS+auth repetido) |
| Engine com pool, 1ª query (inclui connect) | ~2.7s |
| Engine com pool, queries seguintes (**reusado**) | **~0.42s** |

A página dispara vários endpoints juntos → ~5s percebidos. **Causa raiz: reconexão por
request.** A correção é reusar conexões — o que exige um event loop persistente.

**Decisão (negocio.md):** migrar as APIs para **FastAPI/uvicorn**, que tem um loop único e
persistente; ali um engine async com pool module-level é reusado naturalmente, eliminando o
gargalo sem o hack do `NullPool`. O frontend Flask passa a consumir o backend via HTTP.

---

## Fora de Escopo

- O agente de WhatsApp (`app/entrypoint`, `app/agents`, `app/services`, pipeline) — não muda.
- Schema do banco e migrations existentes (0001–0005) — inalterados.
- Regras de negócio financeiras (math em `Decimal`, embeddings) — preservadas, não reescritas.
- Autenticação/multiusuário.
- Trocar o frontend de Flask para outra tecnologia (continua Flask, só reorganizado).

---

## Requisitos Funcionais

### RF-01 · Backend FastAPI em camadas (`backend/`)

Todas as APIs hoje em `dashboard/blueprints/api_*.py` migram para um app FastAPI em `backend/`:

```
backend/
  controllers/   routers FastAPI, sem lógica de negócio
  services/      orquestração + regras de negócio
  dtos/          schemas Pydantic de entrada/saída
  entities/      modelos de domínio
  config.py      pydantic-settings
  main.py        app FastAPI + lifespan (engine pooled)
```

- Engine async **pooled, criado uma vez** no lifespan e reusado entre requests.
- Controllers não contêm lógica; delegam a `services/`.
- Endpoints preservam os contratos JSON atuais (mesmas rotas e formato de resposta) para o
  frontend não quebrar — as rotas passam a ser servidas pelo backend (`:8000`).
- Convenções `python-dev`: `uv`, `pydantic`, `ruff`, `logging` (INFO/DEBUG), sem comentários.
- Na **inicialização**, logar em nível INFO o motivo da lentidão anterior (reconexão por
  request) e a estratégia adotada (pool reusado).

**Critérios de aceitação:**

- [ ] Todas as rotas atuais (`/api/transacoes*`, `/api/grafico/*`, resumo, projeção) respondem pelo backend FastAPI
- [ ] **p95 de cada endpoint < 1s** após o primeiro request (warmup), medido localmente
- [ ] Engine criado uma única vez (não por request); pool reusado
- [ ] Log INFO na subida documentando o gargalo e a correção
- [ ] Controllers sem lógica de negócio (lógica em `services/`)

### RF-02 · Frontend Flask refatorado em camadas (`frontend/`)

```
frontend/
  blueprints/    um Blueprint por funcionalidade (dashboard, lancamentos, relatorios)
  services/      cliente HTTP (httpx) para o backend — sem lógica de negócio
  templates/     Jinja2 por blueprint, espelhando blueprints/
  static/        css/ js/ img/
  config.py      pydantic-settings (ex.: BACKEND_URL)
```

- Views só recebem dados do `service` e passam ao template; **nenhuma regra de negócio**.
- `services/` chamam o backend via `httpx`; nenhum acesso direto ao banco no frontend.

**Critérios de aceitação:**

- [ ] Frontend não importa `app.repositories` nem acessa o banco diretamente
- [ ] Cada funcionalidade é um Blueprint; templates espelham a estrutura
- [ ] `services/` usam httpx contra `BACKEND_URL` (config via pydantic-settings)

### RF-03 · Gráfico de evolução com linha de receitas

O gráfico de evolução passa a ter **três séries**: gastos, investimentos e **receitas**, com
cores e legendas distintas, mesmo padrão visual atual.

**Critérios de aceitação:**

- [ ] Endpoint de evolução retorna `receitas` por mês além de `gastos`/`investimentos`
- [ ] A linha de receitas aparece no gráfico com cor/legenda próprias

### RF-04 · Layout: largura máxima, centralização e responsividade

- Container principal: `max-width: 1400px`, `margin: 0 auto`, padding lateral adequado e
  **borda sutil** delimitando a área de leitura.
- **Mobile-friendly:** abaixo de 1400px o conteúdo é fluido (100% com padding); sem scroll
  horizontal em telas pequenas.

**Critérios de aceitação:**

- [ ] Em monitor largo, o conteúdo fica centralizado com no máx. 1400px e borda visível
- [ ] Em viewport estreita (ex.: 375px), layout fluido, sem overflow horizontal

### RF-05 · Tabela/projeção de 13 meses (−6 … +6)

Evolução e Gastos Mensais exibem **sempre 13 meses**: 6 anteriores + mês atual + 6 futuros.

- Meses passados/atual: dados reais.
- Meses futuros: projeção a partir dos **parcelamentos pendentes** e **receitas registradas**
  com vencimento nesses meses.
- Todos os 13 meses aparecem no eixo, mesmo com valor zero (linha/tabela contínua).

**Critérios de aceitação:**

- [ ] As respostas de evolução e mensal têm exatamente 13 entradas, de −6 a +6 meses
- [ ] Mês com lançamento futuro (parcela/receita) mostra o valor projetado
- [ ] Mês sem dados aparece com zero (não some da série)

### RF-06 · Script de inicialização unificado (`start.py`)

`start.py` na raiz sobe **backend (:8000)** e **frontend (:5000)** juntos.

- Usa `subprocess` para os dois processos.
- Logs dos dois no mesmo terminal com prefixo `[backend]` / `[frontend]`.
- `CTRL+C` encerra ambos de forma limpa (sem processos órfãos).

**Critérios de aceitação:**

- [ ] `uv run python start.py` sobe os dois serviços nas portas indicadas
- [ ] Saída combina logs prefixados por origem
- [ ] `CTRL+C` finaliza backend e frontend sem deixar processo vivo

---

## Contratos a congelar no planejamento

- **`api-endpoints`**: rotas + JSON de cada endpoint migrado (igual ao atual + `receitas` na evolução).
- **`db-engine`**: engine async pooled no lifespan do FastAPI; sessão por request a partir do pool.
- **`frontend-backend`**: `BACKEND_URL`, contrato do cliente httpx, formato consumido pelos templates.
- **`projecao-13-meses`**: definição da janela e da regra de projeção futura (parcelas+receitas).

## Como verificar

| Requisito | Verificação |
|---|---|
| RF-01 | Subir backend; medir cada endpoint (2ª chamada) < 1s; conferir log INFO do gargalo |
| RF-02 | Inspecionar imports do frontend (sem `app.repositories`); testes de service httpx mockado |
| RF-03 | Teste do endpoint de evolução incluindo `receitas`; conferência visual da 3ª linha |
| RF-04 | Teste de template/CSS (max-width 1400, margin auto, borda); checagem responsiva 375px |
| RF-05 | Teste: resposta com 13 meses; mês futuro com projeção; mês vazio com zero |
| RF-06 | Rodar `start.py`; ver dois serviços e logs prefixados; CTRL+C encerra ambos |

## Dúvidas em aberto (resolver no planejamento)

- **Reuso do domínio:** o backend `entities/`/`services/` reaproveita `app/models` e
  `app/repositories` (async, agora pooled) ou recria a camada? (Recomendado reaproveitar o
  repositório existente para não duplicar a lógica de parcelas/embeddings.) pode reaproveirar
- **Projeção futura (RF-05):** projeção = somar apenas parcelas/receitas com `status=PENDENTE` nao, pode ser todas no calculo
  já registradas no mês, ou também repetir os `recorrentes` (GASTOS_FIXOS) nos meses futuros?
- **Portas/config:** confirmar `:8000` backend e `:5000` frontend e variável `BACKEND_URL`. sim, pode confirmar as portas
