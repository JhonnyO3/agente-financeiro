# Contrato: Fronteira frontend (cliente, proxy, DOM)

**Status:** Congelado
**Fronteira:** `backend_client.py`/`api_proxy.py` (T04) ↔ JS (T05/T06) ↔ `index.html`/partials (T05/T06)

## Métodos do `BackendClient` (T04, padrão `_autenticado`)

```python
def atualizar_grupo(self, grupo: str, body: dict) -> httpx.Response   # PUT /api/grupos/{grupo}
def criar_grupo(self, body: dict) -> httpx.Response                   # POST /api/grupos
def listar_gastos_fixos(self) -> httpx.Response                       # GET  /api/gastos-fixos
def criar_gasto_fixo(self, body: dict) -> httpx.Response              # POST /api/gastos-fixos
def atualizar_gasto_fixo(self, id: int, body: dict) -> httpx.Response # PUT  /api/gastos-fixos/{id}
def excluir_gasto_fixo(self, id: int) -> httpx.Response               # DELETE /api/gastos-fixos/{id}
```

## Rotas do proxy Flask (T04, padrão `try/except httpx.HTTPError → 502`, `_repassar`)

| Método/rota Flask | Chama no cliente |
|---|---|
| `PUT  /api/grupos/<grupo>` | `atualizar_grupo(grupo, json)` |
| `POST /api/grupos` | `criar_grupo(json)` |
| `GET  /api/gastos-fixos` | `listar_gastos_fixos()` |
| `POST /api/gastos-fixos` | `criar_gasto_fixo(json)` |
| `PUT  /api/gastos-fixos/<int:id>` | `atualizar_gasto_fixo(id, json)` |
| `DELETE /api/gastos-fixos/<int:id>` | `excluir_gasto_fixo(id)` |

- A rota `DELETE /api/grupos/<grupo>` já existe — **não** reescrever.
- Body via `request.get_json(silent=True) or {}`. Backend fora do ar →
  `({"erro": "backend indisponível"}, 502)`.

## IDs de DOM (fronteira JS ↔ HTML)

### Seção parcelas (T05, em `index.html`)
- `#btn-novo-parcelamento` — botão na seção "Parcelas em andamento".
- Cada card injetado por `app.js`/`grupos.js` ganha botão `.btn-editar-grupo` com
  `data-grupo`, `data-descricao`, `data-valor`, `data-parcela-atual`,
  `data-parcela-total`, `data-proxima-data`.
- `#modal-grupo` (editar/novo, reutilizável): campos `#grupo-descricao`, `#grupo-valor`,
  `#grupo-parcela-atual`, `#grupo-parcela-total`, `#grupo-proxima-data`,
  `#grupo-categoria`, `#grupo-forma-pagamento`, `#grupo-responsavel`,
  hidden `#grupo-id` (vazio = criar); botão `#btn-salvar-grupo`; alvo de erro `#grupo-erro`.

### Seção gastos fixos (T06, em `dashboard/_gastos_fixos.html`, incluído pela T05)
- Contêiner `#gastos-fixos-container`; total `#gastos-fixos-total`;
  vazio `#gastos-fixos-vazio` ("Nenhum gasto fixo cadastrado").
- `#btn-novo-gasto-fixo`.
- `#modal-gasto-fixo`: `#gf-descricao`, `#gf-valor`, `#gf-data`, `#gf-categoria`,
  `#gf-forma-pagamento`, `#gf-responsavel`, hidden `#gf-id`; botão `#btn-salvar-gasto-fixo`;
  erro `#gf-erro`. Itens com `.btn-editar-gasto-fixo`/`.btn-remover-gasto-fixo`
  (`data-id`).

## Pontos de integração que viram dependência no DAG
- T05 adiciona em `index.html`: `{% include "dashboard/_gastos_fixos.html" %}` e
  `<script src="{{ url_for('static', filename='js/gastos_fixos.js') }}">`. T06 **só**
  preenche o partial e o `.js` (não toca `index.html`/`app.js`).
- Aritmética monetária (total mensal, valores) vem **pronta como string do backend**; o JS
  apenas exibe. Proibido somar/quantizar dinheiro no JS.
