# Tarefa 08 — Front base: templates, cards e projeção

**Stack:** python (templates) + js · **Dependências:** 01
**Contratos:** `contracts/dom-v2.md`, `contracts/api-json-v2.md`

## Arquivos que esta tarefa possui
- `dashboard/templates/index.html` · `dashboard/static/app.js`
- `tests/test_dashboard_templates.py`

## O que implementar
1. `index.html`: card `card-receitas` (linha de cards vira 4 colunas), seção
   `projecao-container` (após os gráficos), select `filtro-status`, colunas Status e
   Responsável nos theads (transações e investimentos), campos novos nos modais
   (`edit-status`, `edit-forma-pagamento`, `edit-responsavel`, `edit-detalhes` e
   equivalentes `add-*`) — ids EXATOS do contrato dom-v2
2. `app.js`: preencher `card-receitas`; card Saldo usa o novo `saldo` (sem mudança de
   lógica de cor); nova função que busca `GET /api/projecao` e renderiza tabela
   compacta em `projecao-container` (mês, gastos pendentes, receitas pendentes,
   saldo projetado com cor pelo sinal, qtd parcelas) via createElement/textContent
3. Testes de render: novos ids presentes; select de status com 3 opções; filtro-tipo
   contém RECEITA (vem do enum — se não vier, ajustar contexto em `dashboard/app.py`
   NÃO é desta tarefa: reportar)

## Critérios de aceite
- [ ] Todos os ids novos do contrato presentes no HTML renderizado
- [ ] Projeção renderiza 6 linhas com dados mockados
- [ ] Nenhuma global nova em `window`
- [ ] Testes de template existentes seguem verdes

## Verificação
`uv run pytest tests/test_dashboard_templates.py -v`, `node --check dashboard/static/app.js`, suíte completa.
