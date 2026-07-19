# Spec: Cartões de Crédito e Perfil/Preferências

**Status:** Rascunho para aprovação
**Feature:** cartoes-e-preferencias
**Origem:** [`specs/cartoes-e-preferencias/negocio.md`](negocio.md)

## Contexto

Backend FastAPI em camadas (`backend/controllers` → `services` → `repositories` → `models`),
SQLAlchemy 2.0 async, migrations Alembic (topo atual `0006`), Postgres+pgvector no Railway.
Front React em `react-dashboard/`. Auth JWT; todo dado é isolado por `usuario_id`
(`get_usuario_atual` injeta `UsuarioToken`). Enums em
[`backend/models/enums.py`](../../backend/models/enums.py); modelo de transação em
[`backend/models/transacao.py`](../../backend/models/transacao.py).

Ambas as features seguem o mesmo padrão de camadas do que já existe (ex.: controllers
`transacoes`/`parcelas`, repos, dtos). São **independentes** e podem virar duas entregas.

---

## Fora de Escopo

- Correções do dashboard (spec separada).
- Agente de WhatsApp / pipeline.
- Soft-delete (o projeto é hard-delete; cartões usam desvinculação, ver abaixo).
- Bandeira, últimos 4 dígitos e limite do cartão (removidos do escopo).
- Fatura por ciclo de fechamento (iteração futura; guardamos `dia_fechamento`/`dia_vencimento`
  para viabilizá-la depois).

---

## Feature 5 — Cartões de crédito

### Relacionamentos

- `usuarios (1) → (N) cartoes` — FK `cartoes.usuario_id`.
- `cartoes (1) → (N) transacoes` — FK `transacoes.cartao_id` (nullable).
- Parcelamento (grupo `grupo_parcela_id`) é tratado como unidade: todas as linhas do grupo
  compartilham o mesmo `cartao_id`.

### Modelo de dados

Nova tabela `cartoes` (migration `0007`):

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | serial PK | |
| `usuario_id` | int FK → `usuarios.id` `ON DELETE CASCADE`, `NOT NULL` | isolamento |
| `apelido` | varchar `NOT NULL` | ex.: "Nubank" |
| `dia_fechamento` | int NULL | 1–31 (para fatura futura) |
| `dia_vencimento` | int NULL | 1–31 (para fatura futura) |
| `cor` | varchar NULL | hex para o card no UI |
| `ativo` | bool `NOT NULL default true` | |
| `criado_em` | timestamp `default now()` | |

Vínculo na transação: adicionar `cartao_id int NULL FK → cartoes.id ON DELETE SET NULL` em
`transacoes` (mesma migration). `SET NULL` garante "excluir cartão não apaga transações —
apenas desvincula". Índice em `transacoes(cartao_id)`.

### Backend

**Modelo/repo/dto/service/controller de cartão:**
- `backend/models/cartao.py` — ORM `Cartao` (Base de `models/transacao.py`).
- `backend/repositories/cartao_repository.py` — CRUD por `usuario_id`.
- `backend/dtos/cartao.py` — `CartaoCreate`, `CartaoUpdate`, `CartaoResponse`.
- `backend/services/cartoes.py` — regras + resumo por cartão.
- `backend/controllers/cartoes.py` (`prefix="/api"`, registrar em `CONTROLLERS` de `backend/main.py`):
  - `GET /api/cartoes` → lista do usuário.
  - `POST /api/cartoes` → cria.
  - `PUT /api/cartoes/{id}` → edita (valida posse).
  - `DELETE /api/cartoes/{id}` → exclui; transações vinculadas caem para `cartao_id NULL`.
  - `GET /api/cartoes/{id}/resumo?periodo=mes_atual` → total do período, nº de parcelas em
    aberto, soma restante das parcelas do cartão. Math em `Decimal`.

**Capacidade 1 — listar gastos do cartão** e **Capacidade 2 — filtrar parcelamentos:**
- Estender `GET /api/transacoes` (em `backend/controllers/transacoes.py` +
  `services/transacoes.py::listar`) com os filtros:
  - `cartao_id: int` → só transações daquele cartão.
  - `sem_cartao: bool` → só transações com `cartao_id IS NULL` (para a Capacidade 3).
  - `apenas_parcelas: bool` (ou reusar `parcela_total>1`) → filtra parcelamentos do cartão.
  - Alternativa para parcelas: `GET /api/parcelas-ativas?cartao_id=X` (estender
    `services/parcelas.py::listar_ativas`). Escolher 1 na aprovação; recomendação: filtro
    `cartao_id` no `GET /api/transacoes` cobre o grosso, e `cartao_id` opcional em
    `parcelas-ativas` para a visão de parcelamentos.

**Capacidade 3 — vincular gastos soltos (em lote):**
- Novo endpoint `PATCH /api/transacoes/cartao` — corpo `{ "ids": [int], "cartao_id": int | null }`.
  Usa `get_session_begin`. Valida posse do cartão (se `cartao_id` não-nulo) e isolamento das
  transações (`WHERE id IN (:ids) AND usuario_id = :u`). `cartao_id = null` desvincula.
  Retorno `{ "atualizados": N }`. (Mesmo padrão do `PATCH /api/transacoes/status` da spec de
  correções.)
- Regra de grupo: ao vincular/desvincular uma transação que é parcela (`parcela_total>1`),
  aplicar a **todas** as linhas do mesmo `grupo_parcela_id`.

**Estender criação/edição:**
- `POST/PUT /api/transacoes` e `PUT /api/grupos/{grupo_parcela_id}` passam a aceitar `cartao_id`
  (opcional), validando que o cartão é do usuário; em grupo, aplica a todas as parcelas.

### Frontend (`react-dashboard/`)

- `src/api/cartoes.js` — client dos endpoints (inclui `vincularCartaoLote(ids, cartao_id)`).
- Página **Cartões** (`src/pages/Cartoes.jsx` + rota no `App.jsx`/Navbar): CRUD com cards.
- **Detalhe do cartão:** total comprometido + parcelas em aberto (`/api/cartoes/{id}/resumo`),
  **lista de gastos do cartão** (`GET /api/transacoes?cartao_id=X`) e **filtro de parcelamentos**.
- **Vincular soltos:** uma visão de transações `sem_cartao=true` com seleção múltipla (reusar
  o padrão de checkboxes/bulk da tabela de Transações da spec de correções) + ação "Vincular ao
  cartão X" → `PATCH /api/transacoes/cartao`.
- No `Dashboard.jsx`, seletor de **cartão** no form de transação (`FormBody`) e no modal de
  parcelamento — populado por `GET /api/cartoes`.

### Critérios técnicos

- Isolamento por `usuario_id` em todos os endpoints (cartão de outro usuário → 404).
- `DELETE` de cartão não remove transações (teste: linhas passam a `cartao_id NULL`).
- Vínculo/desvínculo e edição em parcelamento aplicam a todas as parcelas do grupo.
- `PATCH /api/transacoes/cartao`: lote atômico, valida posse do cartão, `cartao_id=null`
  desvincula, rejeita ids vazios.
- Migration idempotente (`upgrade`/`downgrade`) com o índice.
- Testes: CRUD, isolamento, delete-desvincula, resumo por cartão, filtro `cartao_id`/`sem_cartao`,
  vínculo em lote e propagação no grupo.

---

## Feature 6 — Perfil/Preferências e aderência

### Decisões fechadas

1. **Soma das metas ≤ 100%** (o máximo é 100%). Rejeitar/avisar acima disso.
2. **Realizado = % do total de saídas** do período: `realizado_% = valor_categoria ÷
   total_saidas`, com `total_saidas = Σ gastos + Σ investimentos` do período (assim a meta de
   "% em investimentos" também é medível). `renda_mensal` é informativa (pode alimentar um
   indicador de "quanto da renda foi usado", mas **não** é a base da distribuição).
3. **Janela = mês atual** (default).

### Modelo de dados

Nova tabela `preferencias` (migration `0008`), 1 linha por usuário:

| Coluna | Tipo | Notas |
|--------|------|-------|
| `id` | serial PK | |
| `usuario_id` | int FK → `usuarios.id` `ON DELETE CASCADE`, `UNIQUE`, `NOT NULL` | 1:1 |
| `renda_mensal` | `DECIMAL(12,2)` NULL | renda fixa declarada (informativa) |
| `metas` | `JSONB NOT NULL default '{}'` | `{ "ALIMENTACAO": 20, "INVESTIMENTO": 30, ... }` em % |
| `atualizado_em` | timestamp `default now()` | |

> `metas` como JSONB (mapa categoria→percentual) evita tabela filha e casa com o conjunto
> fechado de `CategoriaEnum`. Chaves válidas = categorias existentes; validar no service.

### Backend

- `backend/models/preferencias.py` — ORM `Preferencias`.
- `backend/repositories/preferencias_repository.py` — get/upsert por `usuario_id`.
- `backend/dtos/preferencias.py` — `PreferenciasBody` (chaves ∈ categorias, cada % ∈ [0,100],
  **soma ≤ 100**) e `PreferenciasResponse`.
- `backend/services/preferencias.py` — get/salvar + cálculo de **aderência**.
- `backend/controllers/preferencias.py` (`prefix="/api"`, registrar em `CONTROLLERS`):
  - `GET /api/preferencias` → preferências do usuário (ou objeto vazio/204 se não houver).
  - `PUT /api/preferencias` → upsert (valida soma ≤ 100%).
  - `GET /api/preferencias/aderencia?periodo=mes_atual` → por categoria:
    `{ categoria, meta_pct, realizado_valor, realizado_pct, desvio_pct }`, onde
    `realizado_pct = valor_categoria ÷ total_saidas × 100` e
    `total_saidas = gastos + investimentos` do período. Reusar a agregação por categoria já
    existente (`services/graficos.py` / `resumo`). Math em `Decimal`.

### Frontend (`react-dashboard/`)

- `src/api/preferencias.js`.
- Página **Perfil/Preferências** (`src/pages/Preferencias.jsx` + rota + item na Navbar):
  campo de renda + inputs de % por categoria, com **indicador da soma** que impede passar de
  100% e mostra a folga restante.
- No `Dashboard.jsx`, bloco de **aderência** (só quando há preferências): gráfico meta ×
  realizado por categoria (barras lado a lado ou barra de progresso por categoria), sinalizando
  acima (estouro) vs. abaixo (folga). Reusar `components/charts`/`components/ui`.

### Critérios técnicos

- 1 registro por usuário (`UNIQUE(usuario_id)`; upsert no repo).
- Validação: chaves ∈ `CategoriaEnum`; cada % ∈ [0,100]; **soma ≤ 100** (senão 400/aviso).
- Aderência em `Decimal`, base = total de saídas (gastos+investimentos) do mês; `total_saidas=0`
  → realizado 0% sem divisão por zero.
- Sem preferências → endpoint de aderência responde vazio e o bloco não aparece.
- Isolamento por `usuario_id`.
- Testes: upsert, soma>100 rejeitada, chaves inválidas, aderência (com/sem saídas), período.

---

## Sequenciamento sugerido

Duas trilhas independentes. Dentro de cada uma: `migration → model/repo → dto/service →
controller → api client → página/UI`. Cartões tem os adendos: estender `GET /api/transacoes`
com `cartao_id`/`sem_cartao`, o `PATCH /api/transacoes/cartao` (vínculo em lote) e o `cartao_id`
em criação/edição/grupo. Preferências já está com as 3 decisões fechadas.

DAG: `cartoes` ∥ `preferencias`; cada uma internamente encadeada como acima.
