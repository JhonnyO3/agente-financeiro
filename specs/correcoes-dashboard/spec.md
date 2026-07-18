# Spec: Correções e Melhorias do Dashboard

**Status:** Rascunho para aprovação
**Feature:** correcoes-dashboard
**Origem:** [`specs/correcoes-dashboard/negocio.md`](negocio.md)

## Contexto

Painel React (`react-dashboard/`) consumindo o backend FastAPI (`backend/`). Toda a tela
principal vive em [`react-dashboard/src/pages/Dashboard.jsx`](../../react-dashboard/src/pages/Dashboard.jsx),
que dispara os endpoints em paralelo e renderiza KPIs, gráficos, projeção, parcelas e a
tabela de transações. Matemática financeira é sempre em `Decimal` no backend, nunca no LLM.

Os 4 itens são independentes entre si e podem virar tarefas paralelas.

---

## Fora de Escopo

- Cartões de crédito e preferências/metas (spec separada).
- Agente de WhatsApp, pipeline, embeddings.
- Schema além das colunas/índices citados aqui.

---

## Item 1 — Escala do gráfico "Evolução Financeira"

**Onde:** [`react-dashboard/src/components/charts/LineChart.jsx`](../../react-dashboard/src/components/charts/LineChart.jsx).
Hoje: Chart.js `Line`, eixo Y único, `LinearScale`, três séries no mesmo eixo. Dados vêm de
`GET /api/grafico/evolucao` (13 meses; `backend/services/graficos.py::evolucao`) — **backend
não muda**, é só apresentação.

**Causa:** eixo linear compartilhado esmaga a série pequena quando a maior é ~50× maior.

**Abordagens (decidir 1 na aprovação):**

| # | Abordagem | Prós | Contras |
|---|-----------|------|---------|
| A (recomendada) | Eixo Y **logarítmico** (`type: 'logarithmic'`) | Todas as séries legíveis com 1 eixo; simples | Leitura log é menos intuitiva; exige tratar zeros (min > 0) |
| B | **Dois eixos Y**: Investimentos no eixo direito, Gastos+Receitas no esquerdo | Mantém leitura linear | Duas escalas confundem comparação direta |
| C | Separar Investimentos em **gráfico próprio** | Cada gráfico com escala adequada | Muda o layout; perde a sobreposição |

**Recomendação:** **A (log)** por menor esforço e por atender "R$1.000 não pode ser reta",
com fallback: se a série tiver zeros, usar `min` = 1 e formatar ticks já existentes
(`callback` de `R$ Xk`). Avaliar B se o usuário quiser manter leitura linear.

**Critérios técnicos.**
- Séries com magnitudes 1:50 mostram variação visível.
- Tooltip continua em BRL; ticks legíveis desktop/mobile (respeitar `isMobile`).
- Sem mudança de contrato de API.

---

## Item 2 — Total em "Parcelas Ativas"

**Onde:** cabeçalho da seção "Parcelas Ativas" em `Dashboard.jsx` (bloco `parcelas.length > 0`,
~linha 357). Espelhar o padrão de "Assinaturas & Gastos Fixos" (`sectionHeader` + `sectionMeta`).

**Dados:** já disponíveis no array `parcelas` (de `GET /api/parcelas-ativas`), cada item tem
`valor_parcela`, `parcela_total`, `pagas`. **Backend não muda** — cálculo no cliente:
- `qtd = parcelas.length`
- `total_mensal = Σ Number(p.valor_parcela)`
- `total_restante = Σ (p.parcela_total - p.pagas) × Number(p.valor_parcela)`

**Critérios técnicos.**
- Cabeçalho mostra `N parcelamentos · R$X/mês · R$Y restante`.
- Formatação BRL (`toLocaleString('pt-BR', {style:'currency'})`, helper `BRL` existente).
- Valores conferem com a soma dos cards.

> Opcional: se preferir o total server-side por consistência, adicionar um objeto de resumo
> em `services/parcelas.py::listar_ativas` retornando `{itens, resumo}` — mas muda o contrato
> e o `Dashboard.jsx` (`setParcelas(pa.value.data.itens)`). Default recomendado: **cliente**.

---

## Item 3 — Projeção considerar recorrentes (o item central)

**Onde:** [`backend/services/projecao.py`](../../backend/services/projecao.py).
Hoje `projecao()` pega `janela_meses(hoje)[6:]` (mês atual + 6 futuros) e **soma apenas
linhas com `data` dentro de cada mês** (`repo.listar_por_periodo`). Parcelas entram (têm
linha futura); gastos fixos/receitas recorrentes não.

**Diagnóstico com dados reais (Railway, hoje=2026-07-13):**
- Projeção Ago/2026 = R$1.691,24 = só as 8 parcelas materializadas.
- GASTOS_FIXOS não-parcelados de Jul = R$1.303,90 (recorrem todo mês, mas não são projetados).
- `recorrente = true` em **0** linhas → o flag existe mas ninguém marca, e a projeção o ignora.

### Decisão de negócio a confirmar: como definir "recorrente"

| Opção | Regra | Implicação |
|-------|-------|------------|
| A (recomendada) | Flag explícito `recorrente=true` na transação | Preciso e controlável; **exige** expor o toggle no form (hoje não existe) e o usuário marcar |
| B | Heurística: `categoria=GASTOS_FIXOS` e `parcela_total=1` conta como mensal recorrente | Zero trabalho do usuário; a seção "Assinaturas & Gastos Fixos" já usa GASTOS_FIXOS como sinal; risco de falso-positivo |
| C | A + B: usa o flag; na ausência, cai na heurística de categoria | Robusto durante a transição (base atual tem flag zerado) | Mais lógica |

**Recomendação: C.** Assim a projeção já melhora com a base atual (heurística) e fica precisa
conforme o usuário passa a marcar `recorrente`. Documentar a regra escolhida como log INFO.

### Mudança de comportamento na projeção

Para cada mês `M` da janela futura, o valor projetado de cada tipo passa a ser:

```
projetado(M) = parcelas_lançadas(M)                      # linhas reais com data em M (como hoje)
             + recorrentes_ativos                        # gastos fixos + receitas recorrentes
             − recorrentes_já_lançados_em(M)             # evita contar 2× se já houver linha
```

- **recorrentes_ativos**: derivados do mês de referência (ex.: última ocorrência de cada
  descrição recorrente), replicados para cada mês futuro enquanto "ativos".
- Evitar dupla contagem: se já existe linha materializada daquela recorrência em `M`, não
  somar de novo.
- Manter `qtd_parcelas` e o `saldo = receitas − gastos − investimentos`.
- **Transparência:** cada linha de projeção deve distinguir origem. Sugestão de contrato:
  acrescentar ao `ProjecaoMes` campos opcionais `origem` ou um breakdown
  `{real: ..., projetado: ...}` para o front sinalizar "projetado". Definir na aprovação.

**Arquivos afetados:** `backend/services/projecao.py`, `backend/dtos/graficos.py`
(`ProjecaoMes` se mudar contrato), possivelmente `backend/repositories/transacao_repository.py`
(query de recorrentes), e no front a tabela de Projeção em `Dashboard.jsx` (marcar projetado).
Se a opção envolver o flag (A/C), expor `recorrente` no form de transação (`FormBody`) e no
`POST/PUT /api/transacoes`.

**Critérios técnicos.**
- Projeção de Ago/2026 com a base atual passa a ~R$2.995 (parcelas + gastos fixos), não R$1.691.
- Sem dupla contagem quando há linha real + recorrência no mesmo mês.
- Math em `Decimal`. Testes cobrindo: mês só com parcela, mês só com recorrente, mês com
  ambos, e recorrente já materializado (não dobra).

---

## Item 4 — Transações: filtro de mês default + bulk update de status

**Onde:** tabela de Transações em `Dashboard.jsx` (~linha 385) + `tableReducer`/`INIT_TABLE`;
backend `GET /api/transacoes` e `services/transacoes.py`.

### 4a. Filtro por mês, default mês atual

- Hoje a tabela usa o `periodo` **global** (default `mes_atual`), compartilhado com
  KPIs/gráficos. Desacoplar: dar à tabela um filtro de mês próprio.
- O endpoint já aceita `data_inicio`/`data_fim` (ISO) além de `periodo` — usar um seletor de
  mês que define `data_inicio`/`data_fim` do mês escolhido, default = mês atual.
- Adicionar `mes` (ou par início/fim) ao `INIT_TABLE` e ao `loadTransacoes`.

**Critério:** ao abrir, tabela mostra só o mês atual; controle permite navegar meses; não
afeta os KPIs/gráficos.

### 4b. Bulk update de status

- **Backend (novo endpoint):** `PATCH /api/transacoes/status` com corpo
  `{ "ids": [int], "status": "PAGO" | "PENDENTE" }`. Novo `service.atualizar_status_em_lote`
  que valida `status` no `StatusEnum`, aplica `UPDATE ... WHERE id IN (:ids) AND usuario_id=:u`
  (respeitando isolamento por usuário), retorna `{ "atualizados": N }`. Sessão com commit
  (`get_session_begin`).
- **Frontend:** coluna de checkbox por linha + "selecionar todas as visíveis"; barra de ação
  em lote aparece com ≥1 selecionada, com botões "Marcar PAGO" / "Marcar PENDENTE"; após
  sucesso, `reload()` e limpar seleção.
- Reaproveitar `editarTransacao`? Não — criar `atualizarStatusLote(ids, status)` em
  `react-dashboard/src/api/transacoes.js`.

**Critérios técnicos.**
- 1 requisição para N linhas; atômica; só altera linhas do usuário logado.
- Rejeita `status` inválido (400) e `ids` vazio.
- Testes: lote válido, status inválido, ids de outro usuário (não afeta).

---

## Sequenciamento sugerido

Itens 1, 2 e 4a são de baixo risco e isolados (front + endpoint simples). Item 3 é o de maior
valor e maior cuidado (regra de negócio + possível mudança de contrato + flag no form) —
tratar como tarefa própria com testes. Item 4b adiciona endpoint + UI de seleção.

DAG: `{1, 2, 4a}` paralelos · `3` isolado (decisão de recorrência primeiro) · `4b` isolado.
