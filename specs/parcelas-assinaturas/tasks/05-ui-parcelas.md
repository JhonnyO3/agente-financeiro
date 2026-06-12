# Tarefa 05 — UI: editar e criar parcelamento no dashboard

**Stack:** python (HTML/JS de posse desta task)
**Depende de:** 04
**Contratos:** `contracts/frontend-dashboard.md`, `contracts/api-grupos.md`

## Objetivo

Adicionar à seção "Parcelas em andamento" o botão Editar por card, o botão "+ Novo
parcelamento", o modal reutilizável e o JS que conversa com o proxy (RF-01/RF-02 na UI).

## Arquivos (posse exclusiva)

- `frontend/templates/dashboard/index.html`
- `frontend/static/js/app.js`
- `frontend/static/js/grupos.js` (novo)

## Escopo

1. **`index.html`:** botão `#btn-novo-parcelamento` na seção; `#modal-grupo` com os campos
   do contrato (`#grupo-descricao`, `#grupo-valor`, `#grupo-parcela-atual`,
   `#grupo-parcela-total`, `#grupo-proxima-data`, `#grupo-categoria`,
   `#grupo-forma-pagamento`, `#grupo-responsavel`, hidden `#grupo-id`, `#btn-salvar-grupo`,
   `#grupo-erro`); selects reutilizam Jinja `categorias`. Adicionar
   `{% include "dashboard/_gastos_fixos.html" %}` (partial preenchido pela T06) e
   `<script src="…/grupos.js">` + `<script src="…/gastos_fixos.js">` (arquivo da T06).
   Criar um `_gastos_fixos.html` **vazio mínimo** (placeholder) para o include não quebrar
   — a T06 o substitui (posse do conteúdo é da T06).
2. **`app.js`:** ao injetar cards de parcelas, adicionar `.btn-editar-grupo` com os
   `data-*` do contrato (`data-grupo`, `data-descricao`, `data-valor`,
   `data-parcela-atual`, `data-parcela-total`, `data-proxima-data`). Manter
   `carregarParcelas()` e expor recarga para o `grupos.js` (padrão IIFE + `window.*` já
   usado em `table.js`).
3. **`grupos.js`:** abrir modal em modo criar (vazio) ou editar (preenchido pelos `data-*`);
   `POST`/`PUT` via proxy; `fetchJSON` que extrai `corpo.erro` (padrão `table.js`);
   recarregar parcelas ao salvar; exibir erro em `#grupo-erro`. **Sem aritmética monetária**
   (valores vêm como string).

## Critérios de aceite

- [ ] Card de parcela mostra botão Editar com os `data-*` corretos
- [ ] "+ Novo parcelamento" abre o modal vazio (modo criar)
- [ ] Salvar criar chama `POST /api/grupos`; salvar editar chama `PUT /api/grupos/{id}`
- [ ] Grupo criado/editado aparece na seção sem recarregar a página
- [ ] Erro do backend (400/404) é exibido em `#grupo-erro`
- [ ] Nenhuma soma/quantização de dinheiro no JS

## Verificação local

```bash
uv run pytest tests/frontend/ -v
```

(Validação manual da UI; a lógica monetária é coberta pelos testes de backend.)
