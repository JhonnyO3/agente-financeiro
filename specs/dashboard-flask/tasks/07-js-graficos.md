# Tarefa 07 — JavaScript Gráficos (Chart.js)

**Stack:** python (projeto) / js (arquivo)
**Dependências:** 06
**Contratos:** `contracts/api-json.md`, `contracts/js-interop.md`

---

## Objetivo

Implementar os três gráficos Chart.js do dashboard: pizza de categorias (RF-03),
barras mensais empilhadas (RF-04) e linha de evolução (RF-05).

---

## Arquivos que esta tarefa possui

- `dashboard/static/charts.js`

---

## O que implementar

Arquivo único, IIFE autocontido (ver `contracts/js-interop.md`): lê `PERIODO` da
URL, define `fmtBRL` e `CORES_CATEGORIA` localmente.

### Pizza — `#chart-pizza` (RF-03)

1. `fetch('/api/grafico/categorias?periodo=' + PERIODO)`
2. `new Chart(..., { type: 'doughnut' })` com cores de `CORES_CATEGORIA`
3. Legenda à direita com `categoria — R$ valor (percentual%)` via
   `plugins.legend.labels.generateLabels` ou tooltip customizado
4. `onClick` da fatia: obter a categoria e chamar
   `window.filtrarPorCategoria(categoria)` com a guarda do contrato

### Barras empilhadas — `#chart-barras` (RF-04)

1. `fetch('/api/grafico/mensal')` — **sem** query param de período (sempre 6 meses)
2. `type: 'bar'` com `scales: { x: { stacked: true }, y: { stacked: true } }`
3. Um dataset por categoria (7 categorias de gasto), cores de `CORES_CATEGORIA`
4. Eixo Y formatado em R$; tooltip mostra o breakdown por categoria

### Linha — `#chart-linha` (RF-05)

1. `fetch('/api/grafico/evolucao')`
2. `type: 'line'`, dois datasets: Gastos (`#dc3545`) e Investimentos (`#198754`)
3. Eixo X = labels `"Jun/26"` vindos prontos da API
4. Pontos visíveis e clicáveis (`pointRadius >= 3`)

---

## Critérios de aceite

- [ ] Pizza renderiza apenas as categorias retornadas pela API (já filtradas > 0)
- [ ] Clique na fatia chama `window.filtrarPorCategoria` (com guarda `typeof`)
- [ ] Barras sempre mostram 6 meses, empilhadas por categoria
- [ ] Linha mostra um ponto por mês com dados, duas séries com as cores corretas
- [ ] Nenhuma global criada além das permitidas pelo contrato de interop
- [ ] Falha de fetch não quebra a página (console.error + canvas vazio)

---

## Comando de verificação

```bash
uv run flask --app dashboard.app run --port 5000 &
# Abrir http://localhost:5000 com dados no banco:
# - pizza, barras e linha renderizadas sem erro no console do browser
# - clicar numa fatia da pizza filtra a tabela de transações
```
