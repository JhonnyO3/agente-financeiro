# Exploração: parcelas-assinaturas

Mapa da codebase produzido pelo `explorador` (12/06/2026) para a feature de edição de
parcelamentos + seção de gastos fixos. Entrada: `specs/parcelas-assinaturas/spec.md`.

## 1. Estrutura relevante

### Backend — registro de controllers

`backend/main.py:14-22` — controllers são registrados via lista `CONTROLLERS`:
```
CONTROLLERS = ["transacoes", "resumo", "parcelas", "graficos", "projecao", "auth", "admin"]
```
Adicionar um controller novo exige apenas acrescentar o nome na lista e criar o arquivo
em `backend/controllers/`. Cada controller expõe `router = APIRouter(prefix="/api")`.

### Backend — injeção de sessão

`backend/dependencies.py`:
- `get_session`: sessão sem begin — usada por rotas de leitura.
- `get_session_begin`: `sessionmaker.begin()` — auto-commit/rollback; usada por todas as
  rotas de escrita (POST, PUT, DELETE).

Padrão em `backend/controllers/parcelas.py:13` e `backend/controllers/transacoes.py:51,65,80`.

### Backend — controllers existentes relevantes

`backend/controllers/parcelas.py`:
- `GET /api/parcelas-ativas` — `get_session` + `service.listar_ativas`
- `DELETE /api/grupos/{grupo_parcela_id}` — `get_session_begin` + `service.excluir_grupo`

`backend/controllers/transacoes.py`:
- Parser de body via `_corpo(request)` (linhas 12-17): tenta `request.json()`, retorna `{}` em falha.
- Erros mapeados: `ValidacaoError` → 400, `NaoEncontradaError` → 404.
- POST devolve `JSONResponse(resultado, status_code=201)`.

### Backend — auth

`backend/auth/dependencies.py`:
- `UsuarioToken`: dataclass `usuario_id: int`, `role: str`, `email: str`.
- `get_usuario_atual(request) -> UsuarioToken`: valida Bearer/JWT; lança `HttpErro(401)`.
- Isolamento por `usuario_id` é responsabilidade do service/repository; o controller
  apenas repassa `usuario.usuario_id`.

### Frontend Flask

`frontend/app.py:26-28`: registra `auth.bp`, `dashboard.bp`, `api_proxy.bp`.

`frontend/blueprints/dashboard.py`: `GET /` renderiza `dashboard/index.html` com
`categorias`, `tipos`, `periodos` (de `frontend/config.py`).

**`frontend/services/backend_client.py`** — cliente HTTP com `_autenticado(method, url, **kwargs)`
(refresh automático de token). Métodos existentes: `login`, `logout`, `resumo`,
`grafico_categorias`, `grafico_mensal`, `grafico_evolucao`, `parcelas_ativas`,
`excluir_grupo(grupo)`, `projecao`, `listar_transacoes`, `criar_transacao(body)`,
`atualizar_transacao(id, body)`, `excluir_transacao(id)`.

**`frontend/blueprints/api_proxy.py`** — uma rota por método do cliente, padrão:
`try/except httpx.HTTPError` → `({"erro": "backend indisponível"}, 502)`; repasse de
status/corpo via `_repassar(resposta)`.

### Frontend — HTML (`frontend/templates/dashboard/index.html`)

- `#parcelas-container` (linha 102): row onde o JS injeta os cards de parcelas; a seção
  (linhas 99-104) não tem botão "Novo".
- `#modal-editar` (linha 227): campos `#edit-data`, `#edit-descricao`, `#edit-categoria`,
  `#edit-valor`, `#edit-status`, `#edit-forma-pagamento`, `#edit-responsavel`,
  `#edit-detalhes`; botão `#btn-salvar-editar`.
- `#modal-adicionar` (linha 291): campos `#add-*`; botão `#btn-salvar-adicionar`.
- Não há seção "Gastos fixos" nem modais de parcelas.

### Frontend — JS

- **`app.js`** (IIFE): resumo + projeção + cards de parcelas. `DOMContentLoaded` chama
  `carregarResumo()`, `carregarProjecao()`, `carregarParcelas()`. `fetchJSON` simples
  (linhas 20-26), não extrai corpo de erro.
- **`table.js`** (IIFE): tabela de transações/investimentos + modais editar/adicionar.
  `fetchJSON` mais rico (linhas 38-52), extrai `corpo.erro`. Expõe
  `window.filtrarPorCategoria`; `recarregarTabelas()` não toca em parcelas.
- **`charts.js`** (IIFE): gráficos Chart.js.

## 2. Convenções reais

### Services backend

- Exceções customizadas no service, capturadas no controller → `JSONResponse`:
  `ValidacaoError` → 400, `NaoEncontradaError` → 404, `IdInvalidoError` → 400,
  `GrupoNaoEncontradoError` → 404.
- Validação de body **manual via dict** (`body.get(...)`), não Pydantic nos controllers;
  os DTOs reais são dataclasses em `backend/repositories/dtos.py`.
- `_como_str(campo)`: normalização de enum (duas variantes: `parcelas.py:12` usa
  `hasattr(campo, "value")`; `transacoes.py:29` usa `isinstance(campo, str)`).
- `Decimal` serializado como `str(valor.quantize(Decimal("0.01")))`.

### Testes backend (`tests/backend/test_parcelas.py`, `test_transacoes.py`)

- Sem DB real; sessão fake = `SimpleNamespace()`.
- `app.dependency_overrides[get_session] = _fake` (idem `get_session_begin`).
- Repository mockado: `patch("backend.services.<modulo>.TransacaoRepository", lambda session: repo)`
  com `repo = SimpleNamespace(metodo=AsyncMock(...))`.
- `TestClient(app)`; cleanup via `ExitStack` + `app.dependency_overrides.clear`.
- Fixtures `make_transacao(...)` / `make_parcela(...)`.

### Testes frontend (`tests/frontend/conftest.py`, `test_proxy.py`)

- `backend = MagicMock()` injetado em `app.config["BACKEND_CLIENT"]`.
- `client`: Flask test client com sessão autenticada pré-populada.
- `resposta_factory(status, payload)`: `MagicMock(spec=httpx.Response)`.
- Testes verificam `backend.<metodo>.assert_called_once_with(...)` e repasse de status.

## 3. Código reutilizável

### `TransacaoRepository` (`backend/repositories/transacao_repository.py`)

- `criar(transacao: TransacaoCreate) -> Transacao` — l.18
- `criar_lote(transacoes: list[TransacaoCreate]) -> list[Transacao]` — l.41
- `buscar_por_id(id, usuario_id=None) -> Transacao | None` — l.68
- `buscar_por_grupo(grupo_parcela_id: UUID, usuario_id=None) -> list[Transacao]` — l.75,
  ordenado por `parcela_numero`
- `atualizar(id, dados: TransacaoUpdate, usuario_id=None) -> Transacao` — l.119
  (filtra campos `is not None` via `asdict`)
- `excluir(id, usuario_id=None)` — l.130
- `excluir_grupo(grupo_parcela_id: UUID, usuario_id=None) -> int` (rowcount) — l.137
- `listar_por_periodo(inicio, fim, usuario_id=None) -> list[Transacao]` — l.177
- `listar_por_periodo_com_embedding(...)` — l.190 (undefer do embedding)
- Outros: `buscar_semantico*`, `excluir_por_filtros`, `contar_por_filtros`, `agregar_por_categoria`.

**Não existe** método de listagem por `recorrente=TRUE` — precisa ser criado (RF-03/04).

### DTOs (`backend/repositories/dtos.py`)

- `TransacaoCreate`: `usuario_id, tipo, valor, descricao, categoria, data, parcela_numero,
  parcela_total, grupo_parcela_id, embedding`; defaults `status=PENDENTE`,
  `forma_pagamento=PIX`, `recorrente=False`, `responsavel="Jhonatas"`, `detalhes=None`.
- `TransacaoUpdate`: tudo opcional/None — `tipo, valor, descricao, categoria, data, status,
  forma_pagamento, recorrente, responsavel, detalhes`. Já tem `recorrente`.
  **Não tem `parcela_numero`/`parcela_total`.**

### Helpers de data

`agent/services/parcelas.py` (funções puras):
- `adicionar_meses(data, meses) -> date`: ±N meses preservando o dia, clamp no último dia
  do mês — exatamente a regra da spec.
- `status_por_data(data, hoje=None) -> StatusEnum`: `data < hoje` → PAGO, senão PENDENTE.
- `datas_do_grupo(data_parcela_atual, parcela_atual, parcela_total) -> list[date]`.

`backend/services/janela.py`: `ultimo_dia(mes)`, `janela_meses(hoje)`.

### Enums (`backend/models/enums.py`)

```
TipoEnum:           GASTO, INVESTIMENTO, RECEITA
CategoriaEnum:      ALIMENTACAO, TRANSPORTE, LAZER, EDUCACAO, GASTOS_FIXOS, COMPRAS, GASTOS_PONTUAIS, INVESTIMENTO, RECEITA
StatusEnum:         PAGO, PENDENTE
FormaPagamentoEnum: CARTAO_CREDITO, CARTAO_DEBITO, PIX, BOLETO
```
Todos `str, enum.Enum` (`.value` == nome).

### Regra de status no cadastro (`backend/services/transacoes.py:136-143`)

PIX → `PAGO`; `RECEITA` com `data <= hoje` → `PAGO`; senão `PENDENTE`. Cobre a regra da
spec para gastos fixos.

## 4. Pontos de integração

- **Routers novos:** acrescentar em `CONTROLLERS` (`backend/main.py:14-22`) e criar
  `backend/controllers/grupos.py` / `gastos_fixos.py`.
- **Cliente HTTP:** novos métodos em `frontend/services/backend_client.py` (padrão
  `_autenticado`).
- **Proxy Flask:** novas rotas em `frontend/blueprints/api_proxy.py` (padrão 502).
- **JS:** `app.js:216-220` (`DOMContentLoaded`) ganha `carregarGastosFixos()`; cards de
  parcelas ganham botão Editar; seção ganha "+ Novo parcelamento". Selects de categoria
  podem reutilizar as variáveis Jinja2 `categorias`/`tipos` já passadas ao template.

## 5. Riscos e pegadinhas

- **Embedding deferred** (`backend/models/transacao.py:41-43`): acessar `.embedding` de
  linhas de `buscar_por_grupo` dispara query extra por objeto. Para copiar o embedding ao
  estender grupo, usar undefer explícito ou método análogo a
  `listar_por_periodo_com_embedding`.
- **`grupo_parcela_id` é VARCHAR (UUID string)** (`transacao.py:40`): repositório aceita
  `UUID` e converte com `str()` internamente.
- **`listar_ativas` corta em `date.today()`** (`backend/services/parcelas.py:26`): a spec
  exige incluir pendentes vencidas → mudar o início da janela ou filtrar sem data.
  Testes existentes mockam o repositório, então não quebram; novos testes devem cobrir
  pendente vencida.
- **`TransacaoUpdate` sem `parcela_numero`/`parcela_total`**: edição de grupo exige
  atualização em lote (novo método de repositório ou mutação dos objetos na sessão
  `get_session_begin`).
- **Dois `fetchJSON` no JS**: preferir o padrão de `table.js` (extrai `corpo.erro`) nos
  fluxos com modal.
- **`responsavel` default `"Jhonatas"`**: manter padrão atual (spec não muda).
- **Divergência agente (+30d / fatura +1 mês) vs dashboard (cadeia mensal)**: aceita
  explicitamente na spec.
