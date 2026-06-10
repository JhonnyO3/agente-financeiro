# Contrato: DOM v2 (deltas sobre `specs/dashboard-flask/contracts/js-interop.md`)

**Status:** Congelado
**Usado por:** T08 (produz HTML + app.js), T09 (consome em table.js)

## Novos elementos em `index.html` (T08 é o dono do arquivo)

| Elemento | id | Quem escreve via JS |
|---|---|---|
| Card Receitas (junto aos 3 existentes) | `card-receitas` | app.js (T08) |
| Seção projeção (tabela compacta, sem canvas) | `projecao-container` | app.js (T08) |
| Filtro de status na tabela | `filtro-status` (select: Todos/PAGO/PENDENTE) | table.js (T09) |
| Colunas novas no thead (transações E investimentos) | — (Status e Responsável, entre Tipo e Ações) | linhas: table.js (T09) |
| Campos no modal editar | `edit-status`, `edit-forma-pagamento`, `edit-responsavel`, `edit-detalhes` | table.js (T09) |
| Campos no modal adicionar | `add-status`, `add-forma-pagamento`, `add-responsavel`, `add-detalhes` | table.js (T09) |

- Selects de status: opções PAGO/PENDENTE. Selects de forma: PIX/CARTAO/OUTRO.
- O select `filtro-tipo` ganha a opção RECEITA (vem de `tipos` no contexto do
  template — `dashboard/app.py` deriva de `TipoEnum`, atualiza sozinho; conferir).

## Regras de renderização (table.js, T09)

- Badge de status na célula: `<span class="badge text-bg-success">PAGO</span>` /
  `text-bg-warning` para PENDENTE
- `detalhes` não ganha coluna: vai em `title` (tooltip) na célula Descrição quando
  não vazio
- Nenhuma global nova em `window` (continua valendo só `filtrarPorCategoria`)

## Card Saldo (app.js, T08)

Passa a exibir `saldo` do `/api/resumo` v2 (= receitas − gastos). Lógica de cor
inalterada (sinal da string).
