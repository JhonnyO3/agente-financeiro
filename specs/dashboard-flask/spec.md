# Spec: Dashboard Financeiro (Flask)

## Contexto

Interface web simples para visualizar e gerenciar os dados registrados pelo agente financeiro via WhatsApp. Consome o mesmo banco PostgreSQL do agente. Implementado em Flask + Jinja2 + Chart.js (CDN). Nenhum framework JS pesado — HTML servidor pelo Flask, gráficos renderizados no cliente com Chart.js.

---

## Fora de Escopo

- Autenticação/login (dashboard local/intranet, sem auth)
- Relatórios em PDF/Excel
- Notificações proativas
- Integração com bancos ou corretoras
- Múltiplos usuários
- Dashboard em tempo real (sem WebSocket — recarrega a página)
- Edição em lote via interface (já existe via WhatsApp)

---

## Stack

| Componente | Tecnologia |
|---|---|
| Server | Flask (Python 3.12+, `uv`) |
| Templates | Jinja2 (nativo do Flask) |
| Gráficos | Chart.js via CDN |
| Estilo | Bootstrap 5 via CDN |
| Banco | PostgreSQL (mesmo do agente, mesma `DATABASE_URL`) |
| ORM | SQLAlchemy async (reutilizar `app/repositories/`) |

O dashboard roda em processo separado (`flask run --port 5000`) mas compartilha o código do projeto (mesma venv/uv).

---

## Estrutura de Arquivos

```
dashboard/
  app.py              # Flask app + rotas
  templates/
    base.html         # layout, navbar, CDN links
    index.html        # página principal (todos os widgets)
  static/
    dashboard.js      # inicialização dos gráficos Chart.js
```

---

## Requisitos Funcionais

### RF-01 · Seletor de Período

Dropdown com opções: **Mês atual**, **Mês anterior**, **Últimos 3 meses**, **Últimos 6 meses**, **Ano atual**, **Tudo**.

Ao selecionar, a página recarrega com o período aplicado como query string (`?periodo=mes_atual`). Todos os widgets respeitam o filtro.

**Critérios de aceitação:**
- [ ] Seletor visível no topo da página
- [ ] Todos os gráficos e tabela filtram pelo período escolhido
- [ ] Período padrão = mês atual

---

### RF-02 · Cards de Resumo

Três cards no topo:

| Card | Valor |
|---|---|
| Total Gastos | Soma de `valor` onde `tipo = GASTO` no período |
| Total Investimentos | Soma de `valor` onde `tipo = INVESTIMENTO` no período |
| Saldo (Invest − Gastos) | Diferença, positivo = verde, negativo = vermelho |

**Critérios de aceitação:**
- [ ] Valores calculados em Python com `Decimal` (nunca JS)
- [ ] Cor do Saldo muda conforme sinal
- [ ] Atualiza ao mudar o período

---

### RF-03 · Gráfico de Pizza — Gastos por Categoria

Pizza com a distribuição percentual dos gastos por categoria no período. Categorias: `ALIMENTACAO`, `TRANSPORTE`, `LAZER`, `GASTOS_FIXOS`, `COMPRAS`, `GASTOS_PONTUAIS`, `OUTROS`.

Legenda ao lado com valor absoluto e percentual de cada fatia.

**Critérios de aceitação:**
- [ ] Exibe apenas categorias com valor > 0 no período
- [ ] Mostra `tipo = GASTO` apenas (exclui INVESTIMENTO)
- [ ] Clicável: clicar numa fatia filtra a tabela de transações pela categoria

---

### RF-04 · Gráfico de Barras — Gastos por Mês

Barras verticais agrupadas exibindo o total de gastos por mês dos **últimos 6 meses** (independente do seletor de período). Cada barra segmentada por categoria (stacked bar).

**Critérios de aceitação:**
- [ ] Sempre mostra 6 meses (janela deslizante)
- [ ] Eixo Y em R$
- [ ] Tooltip mostra breakdown por categoria ao passar o mouse

---

### RF-05 · Gráfico de Linha — Evolução Mensal

Duas linhas ao longo do tempo: **Gastos** (vermelho) e **Investimentos** (verde). Exibe todos os meses com dados disponíveis.

**Critérios de aceitação:**
- [ ] Pontos clicáveis no gráfico
- [ ] Eixo X = meses no formato `Jun/26`
- [ ] Exibe todos os meses com pelo menos 1 registro

---

### RF-06 · Seção de Parcelas em Andamento

Cards horizontais para cada grupo de parcelas com status `Próxima` ou `Futura` (data ≥ hoje). Cada card exibe:

```
[Descrição]  Parcela X/N  Próximo: dd/mm/yyyy  R$ valor/parcela
[Barra de progresso visual: X de N pagas]
```

Botão "Excluir grupo" em cada card abre confirmação antes de deletar.

**Critérios de aceitação:**
- [ ] Mostra apenas parcelas com data ≥ hoje
- [ ] Barra de progresso correta (`parcela_numero / parcela_total`)
- [ ] Exclusão do grupo remove todos os registros do `grupo_parcela_id`

---

### RF-07 · Tabela de Transações

Tabela paginada (25 por página) com todas as transações. Colunas:

| Data | Descrição | Categoria | Valor | Parcela | Tipo | Ações |
|---|---|---|---|---|---|---|
| 10/06/2026 | Coxinha | ALIMENTACAO | R$ 100,00 | 1/1 | GASTO | ✏️ 🗑️ |

Filtros acima da tabela: **período** (herda do seletor global) + **tipo** (Gastos/Investimentos/Todos) + **categoria** (dropdown).

**Edição inline:** clicar em ✏️ abre modal com formulário pré-preenchido (campos: data, descrição, categoria, valor). Salvar chama `PUT /api/transacoes/<id>`.

**Inclusão manual:** botão "+ Adicionar" abre modal com formulário vazio. Campos obrigatórios: data, valor, tipo, categoria. Descrição opcional. Salvar chama `POST /api/transacoes`.

**Remoção:** clicar em 🗑️ exibe confirmação inline. Confirmar chama `DELETE /api/transacoes/<id>`.

**Critérios de aceitação:**
- [ ] Paginação funciona corretamente
- [ ] Filtros combinados funcionam (período + tipo + categoria)
- [ ] Modal de edição pré-preenche todos os campos
- [ ] Inclusão manual cria registro com `parcela_numero=1`, `parcela_total=1`, `grupo_parcela_id` gerado em Python
- [ ] Remoção é hard delete (sem soft delete)
- [ ] Após qualquer CRUD a tabela atualiza sem recarregar a página inteira (fetch + re-render do trecho)

---

### RF-08 · Seção de Investimentos

Tabela separada (mesma estrutura da RF-07) filtrada em `tipo = INVESTIMENTO`. Card acima com total investido no período e total histórico.

**Critérios de aceitação:**
- [ ] Total histórico usa `date(2000,1,1)` como piso (consistente com o agente)
- [ ] Edição/remoção funcionam igual à tabela geral

---

## API Endpoints (Flask)

Todas as rotas retornam JSON. Calculado em Python, nunca delegado ao JS.

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Página principal (HTML) |
| GET | `/api/resumo` | Cards de totais `{gastos, investimentos, saldo}` |
| GET | `/api/grafico/categorias` | Dados para pizza `[{categoria, total, percentual}]` |
| GET | `/api/grafico/mensal` | Dados barras 6 meses `[{mes, por_categoria: {...}}]` |
| GET | `/api/grafico/evolucao` | Dados linha `[{mes, gastos, investimentos}]` |
| GET | `/api/parcelas-ativas` | Grupos com parcela futura/próxima |
| GET | `/api/transacoes` | Lista paginada `{itens, total, pagina, paginas}` |
| POST | `/api/transacoes` | Criar transação manual |
| PUT | `/api/transacoes/<id>` | Editar transação |
| DELETE | `/api/transacoes/<id>` | Excluir transação |
| DELETE | `/api/grupos/<grupo_parcela_id>` | Excluir grupo de parcelas |

**Query params comuns:** `?periodo=mes_atual&tipo=GASTO&categoria=ALIMENTACAO&pagina=1`

**Períodos válidos:** `mes_atual`, `mes_anterior`, `ultimos_3_meses`, `ultimos_6_meses`, `ano_atual`, `tudo`

---

## Modelo de Dados (reutilizado do agente)

Tabela `transacoes` — nenhuma migration nova necessária. O dashboard apenas lê e escreve na mesma tabela.

Para inclusão manual via dashboard, o embedding pode ser `NULL` (coluna já é `nullable=True`).

---

## Como Verificar

| Requisito | Como testar |
|---|---|
| RF-01 | Mudar seletor → todos os números e gráficos mudam |
| RF-02 | Inserir 3 registros conhecidos → conferir soma nos cards |
| RF-03 | Pizza exibe só categorias com valor; clicar filtra tabela |
| RF-04 | Barras mostram exatamente os últimos 6 meses |
| RF-05 | Linha tem 1 ponto por mês com dados; tooltip correto |
| RF-06 | Parcela vencida (data < hoje) não aparece nos cards |
| RF-07 | Editar valor → conferir no banco via SELECT |
| RF-07 | Adicionar registro manual → aparece na tabela e no banco |
| RF-07 | Deletar → sumiu do banco (hard delete) |
| RF-08 | Tabela investimentos só mostra `tipo = INVESTIMENTO` |
