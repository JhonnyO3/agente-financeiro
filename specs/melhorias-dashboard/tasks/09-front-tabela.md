# Tarefa 09 — Front tabela: badges, filtro status e modais v2

**Stack:** js · **Dependências:** 07 (contrato congelado), 08 (DOM)
**Contratos:** `contracts/dom-v2.md`, `contracts/api-json-v2.md`

## Arquivos que esta tarefa possui
- `dashboard/static/table.js`

## O que implementar
1. Linhas das duas tabelas ganham células Status (badge `text-bg-success`/PAGO,
   `text-bg-warning`/PENDENTE) e Responsável, na posição do thead (entre Tipo e Ações)
2. `detalhes` não vazio → `title` (tooltip) na célula Descrição
3. Filtro `filtro-status`: entra no estado e na query string do fetch, combinando com
   tipo/categoria; reset para página 1 ao mudar
4. Modal editar: pré-preencher e enviar `status`, `forma_pagamento`, `responsavel`,
   `detalhes` no PUT; modal adicionar: incluir os campos no POST
5. Sem aritmética monetária; valores seguem strings

## Critérios de aceite
- [ ] Badges corretos por status nas duas tabelas
- [ ] Filtro status + tipo + categoria combinados na query string
- [ ] PUT/POST enviam os novos campos; editar pré-preenche a partir do item
- [ ] Única global continua sendo `filtrarPorCategoria`

## Verificação
`node --check dashboard/static/table.js`; `uv run pytest tests/ -q` segue verde;
verificação visual no browser fica para o smoke final da feature.
