# Plano Técnico — parcelas-assinaturas

**Status:** Aprovado
**Spec:** `specs/parcelas-assinaturas/spec.md` (Aprovada)
**Contratos:** `contracts/datas-parcela.md` (Congelado), `contracts/repositorio-grupos.md` (Congelado), `contracts/api-grupos.md` (Congelado), `contracts/api-gastos-fixos.md` (Congelado), `contracts/frontend-dashboard.md` (Congelado)

> Aprovado pelo usuário em 12/06/2026 (autorizou execução pela squad em branch dedicada).

## Arquitetura da mudança

A feature toca duas camadas (backend FastAPI e frontend Flask), em três frentes de
domínio (edição/criação de grupos de parcelas, gastos fixos, e UI). Nada de migração de
banco: usa colunas existentes (`recorrente`, `grupo_parcela_id`, `parcela_numero`,
`parcela_total`, `embedding`).

Camadas afetadas (seguindo o padrão real do projeto):

```
backend/controllers/   → grupos.py (novo), gastos_fixos.py (novo); CONTROLLERS atualizado
backend/services/      → grupos.py (novo), gastos_fixos.py (novo); datas_parcela.py (novo, helpers puros); parcelas.py (listar_ativas ajustado)
backend/repositories/  → transacao_repository.py (3 métodos novos)
frontend/services/     → backend_client.py (métodos novos)
frontend/blueprints/   → api_proxy.py (rotas novas)
frontend/templates/    → dashboard/index.html (seções/modais novos) + dashboard/_gastos_fixos.html (novo)
frontend/static/js/    → app.js (parcelas: editar/novo) + grupos.js/gastos_fixos.js (novos)
```

Fluxo de dependência entre camadas é **agent → backend** (o agente já importa
`backend.models.enums` e `backend.repositories`). O backend **nunca** importa de `agent`.

### Frentes

1. **Base compartilhada (T01):** helpers de data puros no backend + métodos novos de
   repositório. É a fonte dos contratos `datas-parcela` e `repositorio-grupos`; T02/T03
   dependem dela. Ajusta `listar_ativas` para incluir pendentes vencidas (RF-01).
2. **Grupos de parcelas (T02):** service + controller de `PUT /api/grupos/{id}` (editar,
   RF-01) e `POST /api/grupos` (criar, RF-02). Registro em `CONTROLLERS`.
3. **Gastos fixos (T03):** service + controller do CRUD `GET/POST/PUT/DELETE
   /api/gastos-fixos` (RF-03/RF-04). Registro em `CONTROLLERS`.
4. **Proxy + cliente frontend (T04):** rotas no `api_proxy.py` e métodos no
   `backend_client.py` para todos os endpoints novos (RF-05).
5. **UI parcelas (T05):** botão Editar/Novo nos cards, modais e JS de grupos.
6. **UI gastos fixos (T06):** seção nova, modais e JS de gastos fixos.

### Anti-colisão (regra inviolável)

`backend/main.py` é tocado por T02 **e** T03 (ambos acrescentam à lista `CONTROLLERS`).
Para não compartilhar arquivo entre tarefas paralelas, **T03 depende de T02** (DAG abaixo).
Os arquivos de service/controller de cada uma são disjuntos.

No frontend, `index.html`, `app.js`, `api_proxy.py` e `backend_client.py` seriam tocados
por mais de uma frente de UI. Resolução:

- `api_proxy.py` e `backend_client.py` ficam **inteiros** com T04 (proxy/cliente é frente
  única; T05/T06 dependem de T04 para ter os métodos prontos).
- `index.html` e `app.js` ficam com T05 (parcelas). T06 (gastos fixos) **não** toca
  `index.html`/`app.js`: a seção de gastos fixos é um partial Jinja incluído
  (`dashboard/_gastos_fixos.html`, novo) e o JS vai em `gastos_fixos.js` (novo, carregado
  por `<script>` próprio). T06 depende de T05 só pelo ponto de inclusão do partial e do
  `<script>` (uma linha cada), tornando-se dependência no DAG.

## Decisões

- **Onde vive a lógica de grupo: novo `backend/services/grupos.py`.** `parcelas.py` hoje é
  só leitura/exclusão; misturar edição/criação transacional (lote, renumeração,
  atomicidade) infla o módulo. Service novo, coeso, espelha o par
  `transacoes.py`/`parcelas.py`. `parcelas.py` recebe só o ajuste mínimo de `listar_ativas`.
- **Helpers de data no backend (não importar do agent): novo `backend/services/datas_parcela.py`.**
  `adicionar_meses`/`status_por_data`/`datas_do_grupo` são funções puras (só dependem de
  `backend.models.enums`). O backend **não pode importar `agent`** (camadas e deploys
  Docker separados). Como editar `agent/services/parcelas.py` está fora de escopo (spec:
  "sem mudanças no agente"), **duplicamos** as 3 funções puras no novo módulo backend. São
  triviais, testadas independentemente, e a duplicação é o preço de manter a fronteira
  agent/backend limpa sem mexer no agente. Decisão registrada no contrato `datas-parcela`.
- **Edição em lote sem estender `TransacaoUpdate`: mutação dos objetos ORM na sessão
  `get_session_begin`.** O `PUT /api/grupos` precisa alterar `parcela_numero`/`parcela_total`
  (que `TransacaoUpdate` não tem) e criar/excluir linhas atomicamente. A via mais limpa e
  alinhada ao projeto é o service carregar o grupo com `buscar_por_grupo_com_embedding`,
  mutar os atributos dos objetos ORM na própria sessão transacional, e usar
  `criar_lote`/novo `excluir_por_grupo_e_numeros` para as diferenças. A atomicidade vem do
  `sessionmaker.begin()` (commit/rollback automático). **Não** estendemos `TransacaoUpdate`
  nem o método genérico `atualizar` (evita acoplar o CRUD unitário a parcelas).
- **Copiar embedding (deferred) ao estender grupo:** `buscar_por_grupo_com_embedding` faz
  `undefer(Transacao.embedding)` (análogo a `listar_por_periodo_com_embedding`). Cada linha
  nova nasce com `embedding` copiado de uma linha existente do grupo. Grupos/gastos fixos
  **criados** pelo dashboard nascem com `embedding=NULL` (igual `POST /api/transacoes`).
- **Renumeração ao diminuir o total:** novo total < total atual ⇒ excluir linhas com
  `parcela_numero > novo_total`; as restantes têm `parcela_total = novo_total`. Como
  `parcela_numero` das restantes já é 1..novo_total, não há renumeração de número — só
  ajuste de `parcela_total`. Ao aumentar, criam-se linhas `atual+1..novo_total`.
- **`listar_ativas` deixa de cortar em `date.today()`:** a janela passa a começar num piso
  fixo no passado (`date(2000, 1, 1)`; teto continua `_DATA_TETO`), mantendo só o filtro
  `parcela_total > 1` e "tem pendente". Assim grupos com pendente vencida não somem
  (RF-01). Testes existentes mockam o repositório e não quebram.
- **Gastos fixos = flag `recorrente` (sem tabela):** novo método de repositório
  `listar_recorrentes(usuario_id)`; service `gastos_fixos.py` reusa a regra de status do
  cadastro (PIX→PAGO, senão PENDENTE) e a serialização Decimal-como-string. `404` quando a
  linha não é `recorrente=TRUE`, não existe ou é de outro usuário.
- **Decimal sempre no backend:** total mensal de gastos fixos e valores de parcela somados
  com `Decimal`, serializados como `str(v.quantize(Decimal("0.01")))`. O JS nunca faz
  aritmética monetária — só exibe strings.
- **Categoria default do `POST /api/grupos`: `COMPRAS`** (a UI permite escolher outra).
- **Frontend partial + script próprio para gastos fixos:** evita colisão de
  `index.html`/`app.js` entre T05 e T06 (ver anti-colisão).

## Tarefas (DAG)

| ID | Tarefa | Stack | Depende de | Arquivos (posse) |
|----|--------|-------|-----------|------------------|
| 01 | Base: helpers de data backend + métodos de repositório + ajuste `listar_ativas` | python | — | `backend/services/datas_parcela.py`, `backend/repositories/transacao_repository.py`, `backend/services/parcelas.py`, `tests/backend/test_datas_parcela.py`, `tests/backend/test_repositorio_grupos.py` |
| 02 | Service+controller de grupos (PUT editar, POST criar) | python | 01 | `backend/services/grupos.py`, `backend/controllers/grupos.py`, `backend/main.py`, `tests/backend/test_grupos.py` |
| 03 | Service+controller de gastos fixos (GET/POST/PUT/DELETE) | python | 02 | `backend/services/gastos_fixos.py`, `backend/controllers/gastos_fixos.py`, `tests/backend/test_gastos_fixos.py` |
| 04 | Proxy Flask + cliente HTTP para os endpoints novos | python | 02, 03 | `frontend/blueprints/api_proxy.py`, `frontend/services/backend_client.py`, `tests/frontend/test_proxy_parcelas_assinaturas.py` |
| 05 | UI parcelas: editar/novo (cards, modais, JS) | python | 04 | `frontend/templates/dashboard/index.html`, `frontend/static/js/app.js`, `frontend/static/js/grupos.js` |
| 06 | UI gastos fixos: seção, modais, JS | python | 05 | `frontend/templates/dashboard/_gastos_fixos.html`, `frontend/static/js/gastos_fixos.js` |

Notas do DAG:
- **02 → 03** por `backend/main.py` (`CONTROLLERS`): T02 cria o registro do router de
  grupos; T03 acrescenta `gastos_fixos`. Não compartilham o arquivo em paralelo.
- **04 depende de 02 e 03** para garantir ordem de integração estável (o proxy implementa
  contra contratos congelados, mas só é testado de ponta a ponta com a API pronta).
- **05 → 06** por `index.html`/`app.js`: T05 inclui o `{% include %}` do partial e o
  `<script src=".../gastos_fixos.js">`; T06 preenche o partial e o JS.

## Ordem de integração

1. T01 (merge primeiro — congela os helpers e o repositório no código).
2. T02 (grupos) → T03 (gastos fixos) — nessa ordem por `backend/main.py`.
3. T04 (proxy/cliente).
4. T05 (UI parcelas) → T06 (UI gastos fixos).
5. Rodar suíte completa `uv run pytest tests/ -v` ao fim de cada merge.

## Riscos

- **Embedding deferred:** copiar embedding ao estender grupo sem `undefer` dispara N
  queries ou retorna `None`. Mitigação: `buscar_por_grupo_com_embedding` (T01) com
  `undefer`. Coberto por teste de repositório.
- **Atomicidade do PUT:** se o service não respeitar a fronteira da sessão
  `get_session_begin`, uma falha no meio deixa o grupo inconsistente. Mitigação: toda a
  mutação acontece numa única sessão transacional.
- **`listar_ativas` ampliando a janela:** com piso antigo, grupos já quitados não devem
  aparecer — o filtro "tem pendente" garante isso. Teste de pendente vencida + grupo quitado.
- **Colisão de arquivos no frontend:** mitigada pelo desenho de partial+script e pelas
  dependências 04→05→06.
- **Renumeração ao diminuir total:** off-by-one no corte `parcela_numero > novo_total`.
  Coberto por cenário Gherkin de diminuir total.

## Verificação da feature

- `uv run pytest tests/ -v` verde (backend + frontend).
- RF-01: `tests/backend/test_grupos.py` — título/valor/data/atual/total, atomicidade,
  400/404; pendente vencida listada em `tests/backend/test_parcelas.py`.
- RF-02: `tests/backend/test_grupos.py` — 12 linhas, mesmo grupo, status por parcela atual,
  validações 400.
- RF-03/04: `tests/backend/test_gastos_fixos.py` — filtro `recorrente`, isolamento por
  usuário, total em `Decimal`, 404 não-recorrente/outro usuário, validações 400.
- RF-05: `tests/frontend/test_proxy_parcelas_assinaturas.py` — repasse de status e 502.
- Cenários Gherkin do QA por tarefa cobrindo RF-01..RF-05.
