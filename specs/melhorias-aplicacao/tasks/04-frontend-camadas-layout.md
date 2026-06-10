# Tarefa 04 — Frontend em camadas, proxy, layout e linha de receitas

**Stack:** python
**Depende de:** contratos (congelados)
**Contratos:** `frontend-backend.md`, `api-endpoints.md`

## Objetivo

Reorganizar o frontend Flask em camadas, proxyar `/api/*` para o backend, aplicar o layout
(max-width 1400, centralizado, borda, mobile-friendly) e adicionar a **linha de receitas** ao
gráfico de evolução.

## Arquivos (posse exclusiva)

- `frontend/__init__.py`, `frontend/app.py`, `frontend/config.py`
- `frontend/blueprints/**` (páginas + `api_proxy`), `frontend/services/backend_client.py`
- `frontend/templates/**` (base + por blueprint), `frontend/static/{css,js,img}/**`
  (migrar `app.js`, `charts.js`, `table.js`; ajustar `charts.js` para a 3ª linha)
- `tests/frontend/**`

## Escopo

1. Estrutura: `blueprints/` (1 por funcionalidade: dashboard, lancamentos, relatorios),
   `services/backend_client.py` (httpx → `BACKEND_URL`), `templates/` espelhando blueprints,
   `static/` por tipo. `config.py` (pydantic-settings: `BACKEND_URL`, `FRONTEND_PORT`).
2. **Proxy** `/api/*`: rotas espelho que chamam o `backend_client` e devolvem `(json, status)`.
   Browser segue buscando same-origin; `app.js/charts.js/table.js` não mudam de URL.
3. **Layout (RF-04):** container `max-width:1400px; margin:0 auto`, padding lateral, **borda sutil**.
   Mobile-friendly: <1400px fluido (100% + padding), sem overflow horizontal em ~375px.
4. **RF-03:** `charts.js` desenha a série **receitas** na evolução (cor/legenda próprias), lendo o
   campo `receitas` do endpoint.
5. Views sem lógica de negócio (só repassam dados do service ao template).

## Critérios de aceite

- [ ] Frontend não importa `app.repositories` nem acessa o banco
- [ ] `/api/*` proxiam ao backend via httpx; status/erros repassados (502 se backend down)
- [ ] Container 1400px centralizado com borda; sem overflow horizontal a 375px
- [ ] Evolução renderiza 3 linhas (gastos, investimentos, receitas)

## Verificação local

```bash
uv run pytest tests/frontend -v
```
