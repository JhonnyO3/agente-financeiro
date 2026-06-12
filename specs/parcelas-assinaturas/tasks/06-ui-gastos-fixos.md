# Tarefa 06 — UI: seção e CRUD de gastos fixos no dashboard

**Stack:** python (HTML/JS de posse desta task)
**Depende de:** 05
**Contratos:** `contracts/frontend-dashboard.md`, `contracts/api-gastos-fixos.md`

## Objetivo

Renderizar a seção "Gastos fixos" (abaixo de "Parcelas em andamento"), com listagem, total
mensal, e modais de incluir/editar/remover (RF-03/RF-04 na UI), sem tocar
`index.html`/`app.js` (já preparados pela T05).

## Arquivos (posse exclusiva)

- `frontend/templates/dashboard/_gastos_fixos.html` (conteúdo; o include vem da T05)
- `frontend/static/js/gastos_fixos.js` (novo, carregado pela T05)

## Escopo

1. **`_gastos_fixos.html`:** seção com `#gastos-fixos-container`, total `#gastos-fixos-total`,
   vazio `#gastos-fixos-vazio` ("Nenhum gasto fixo cadastrado"), `#btn-novo-gasto-fixo` e
   `#modal-gasto-fixo` (`#gf-descricao`, `#gf-valor`, `#gf-data`, `#gf-categoria`,
   `#gf-forma-pagamento`, `#gf-responsavel`, hidden `#gf-id`, `#btn-salvar-gasto-fixo`,
   `#gf-erro`). Selects reutilizam Jinja `categorias`.
2. **`gastos_fixos.js`:** `carregarGastosFixos()` chama `GET /api/gastos-fixos`, renderiza
   itens (título, valor string, dia, categoria, forma, ações editar/remover com `data-id`),
   exibe `total_mensal` (string, sem somar no JS) e o estado vazio; modais POST/PUT;
   remover com confirmação antes do DELETE; `fetchJSON` que extrai `corpo.erro`. Chamada
   inicial em `DOMContentLoaded` própria do arquivo. **Sem aritmética monetária no JS.**

## Critérios de aceite

- [ ] Seção lista só os gastos fixos do usuário (vindos do backend), ordenados por dia
- [ ] Exibe título, valor, dia, categoria, forma de cada item e o total mensal (string)
- [ ] Lista vazia mostra "Nenhum gasto fixo cadastrado"
- [ ] Incluir/editar abrem o modal e chamam POST/PUT; item reflete após salvar
- [ ] Remover pede confirmação e chama DELETE; item some da seção
- [ ] Nenhuma soma/quantização de dinheiro no JS

## Verificação local

```bash
uv run pytest tests/frontend/ -v
```

(Validação manual da UI; total mensal é calculado e testado no backend.)
