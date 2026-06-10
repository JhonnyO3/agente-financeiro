# Contrato: Interop JavaScript (Dashboard)

**Status:** Congelado
**Usado por:** T06 (carrega os scripts), T07, T08, T09 (implementam)

---

## Princípio

Os três arquivos JS (`charts.js`, `table.js`, `app.js`) são implementados por tarefas
paralelas. Este contrato congela a interface entre eles para evitar colisão.

## Regras gerais

1. **Cada arquivo é um IIFE autocontido** — nenhuma variável global além das
   explicitamente listadas abaixo. Helpers (formatação BRL, fetch) são duplicados
   em cada arquivo, não compartilhados.
2. **Ordem de carga** (definida em `base.html`): `charts.js` → `table.js` → `app.js`.
   Nenhum arquivo pode depender de outro em tempo de carga — interações só via
   eventos de usuário (quando todos já carregaram).
3. **Período atual**: cada arquivo lê por conta própria:
   ```js
   const PERIODO = new URLSearchParams(location.search).get("periodo") || "mes_atual";
   ```
   Todo fetch a endpoints que aceitam período inclui `?periodo=${PERIODO}`.
4. **Formatação monetária**: valores chegam como string decimal (`"350.00"`).
   Exibir com:
   ```js
   function fmtBRL(s) {
     return Number(s).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
   }
   ```
   (apenas exibição — nunca aritmética em JS).

## Globais expostas (únicas permitidas)

| Global | Definida por | Consumida por | Assinatura |
|--------|-------------|---------------|------------|
| `window.filtrarPorCategoria` | `table.js` (T08) | `charts.js` (T07, clique na pizza) | `(categoria: string) => void` — seta o filtro de categoria da tabela de transações, volta à página 1 e re-renderiza |

`charts.js` deve chamar com guarda:
```js
if (typeof window.filtrarPorCategoria === "function") {
  window.filtrarPorCategoria(categoria);
}
```

## Posse dos elementos do DOM (ids definidos em T06)

| Elemento | Quem escreve via JS |
|----------|---------------------|
| `#card-gastos`, `#card-investimentos`, `#card-saldo` | `app.js` (T09) |
| `#parcelas-container` | `app.js` (T09) |
| `#chart-pizza`, `#chart-barras`, `#chart-linha` | `charts.js` (T07) |
| `#tabela-transacoes`, `#paginacao`, `#filtro-tipo`, `#filtro-categoria` | `table.js` (T08) |
| `#modal-editar`, `#modal-adicionar` | `table.js` (T08) |
| `#tabela-investimentos`, `#card-invest-periodo`, `#card-invest-total` | `table.js` (T08) |

## Cores fixas por categoria (pizza e barras usam o mesmo mapa)

```js
const CORES_CATEGORIA = {
  ALIMENTACAO:      "#fd7e14",
  TRANSPORTE:       "#0d6efd",
  LAZER:            "#6f42c1",
  GASTOS_FIXOS:     "#dc3545",
  COMPRAS:          "#d63384",
  GASTOS_PONTUAIS:  "#ffc107",
  OUTROS:           "#6c757d",
};
```

## Tratamento de erro de fetch

Em caso de resposta não-2xx ou falha de rede: `console.error` e deixar o widget
com o placeholder (`—` ou vazio). Sem alertas bloqueantes para erros de leitura.
