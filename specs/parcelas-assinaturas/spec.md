# Spec: Parcelas e Assinaturas — edição de parcelamentos e seção de gastos fixos

**Status:** Aprovado
**Feature:** parcelas-assinaturas
**Origem:** pedido do usuário (12/06/2026) — (1) editar parcelas em andamento no dashboard;
(2) nova seção de gastos fixos com inclusão, edição e remoção.

## Contexto

O dashboard tem a seção **"Parcelas em andamento"** que hoje só lista os grupos de
parcelas e permite excluir o grupo inteiro (`GET /api/parcelas-ativas`,
`DELETE /api/grupos/{grupo_parcela_id}`). Não há edição nem criação de parcelamento
pelo dashboard.

O conceito de **gasto fixo** já existe no modelo: transações com `recorrente = TRUE`
(coluna criada em melhorias-cadastramento), uma linha por assinatura
(`parcela_numero = parcela_total = 1`), consideradas ativas todos os meses pela
projeção. O agente do WhatsApp já grava assim (Claude, inglês, academia, luz etc.),
mas **não existe UI** para ver ou gerenciar esses registros.

### Estado atual (código)

- Parcelas: uma linha de `transacoes` por parcela, todas com o mesmo
  `grupo_parcela_id` (UUID) e o mesmo embedding; última parcela absorve resto da divisão.
- `backend/services/parcelas.py`: `listar_ativas` agrupa pendentes com
  `parcela_total > 1` a partir de hoje; `excluir_grupo` remove o grupo todo.
- `backend/services/transacoes.py`: CRUD unitário de transações
  (`POST/PUT/DELETE /api/transacoes`), sem suporte ao campo `recorrente` no body.
- Frontend Flask: proxy explícito por rota em `frontend/blueprints/api_proxy.py` +
  cliente HTTP em `frontend/services`; seção de parcelas renderizada por
  `frontend/static/js/app.js` (cards Bootstrap); já há padrão de modais
  (`modal-editar`, `modal-adicionar`) em `frontend/templates/dashboard/index.html`.

---

## Fora de escopo

- Geração automática de lançamentos mês a mês a partir de recorrentes (mantém o
  modelo de flag; projeção continua consumindo `recorrente = TRUE`).
- Mudanças no agente do WhatsApp (fluxos de cadastro/edição por mensagem ficam como estão).
- Embeddings para linhas criadas/alteradas pelo dashboard (novas linhas de grupo
  copiam o embedding existente do grupo; grupos e gastos fixos criados pelo dashboard
  ficam com embedding `NULL`, como o `POST /api/transacoes` já faz).
- Notificação de vencimento.
- Alterações em resumo/projeção/gráficos (consomem as mesmas linhas; refletem
  automaticamente as edições).

---

## Requisitos funcionais

### RF-01 · Editar grupo de parcelas

Cada card da seção "Parcelas em andamento" ganha um botão **Editar** que abre um modal
com os campos:

| Campo | Efeito |
|---|---|
| Título (`descricao`) | Aplicado a **todas** as linhas do grupo (pagas e pendentes). |
| Valor da parcela | Aplicado a todas as parcelas **pendentes**; pagas não mudam. |
| Data de vencimento | Nova data vale para a **próxima parcela pendente**; as pendentes seguintes são recalculadas mês a mês a partir dela (+1 mês preservando o dia, ajustado ao último dia do mês quando necessário). Parcelas pagas não mudam. |
| Parcela atual | Define o progresso: linhas com `parcela_numero` menor que a atual ficam `PAGO`; da atual em diante ficam `PENDENTE`. |
| Última parcela (`parcela_total`) | Aumentar cria novas linhas no fim do grupo (mesmo `grupo_parcela_id`, valor da parcela do formulário, categoria/forma/responsável/embedding copiados do grupo, datas continuando a cadeia mensal). Diminuir exclui as linhas finais. Todas as linhas do grupo têm `parcela_total` atualizado. |

Regras e validações:

- Novo total não pode ser menor que a parcela atual informada nem menor que 1 → `400`.
- Valor da parcela deve ser maior que zero → `400`.
- `grupo_parcela_id` malformado → `400`; grupo inexistente ou de outro usuário → `404`.
- A operação é atômica: ou todas as linhas do grupo são ajustadas, ou nenhuma.
- A listagem de parcelas ativas passa a incluir grupos com parcelas pendentes
  **vencidas** (`data` no passado), para que um grupo editado para uma data passada
  não suma da seção.

Endpoint novo: `PUT /api/grupos/{grupo_parcela_id}` (detalhe congelado em `contracts/`
na fase de planejamento).

**Critérios de aceitação:**

- [ ] Editar o título altera `descricao` de todas as linhas do grupo
- [ ] Editar o valor altera apenas as parcelas `PENDENTE`
- [ ] Editar a data move a próxima pendente e recalcula as seguintes mês a mês; pagas intactas
- [ ] Parcela atual = N marca 1..N-1 como `PAGO` e N..total como `PENDENTE`
- [ ] Aumentar o total cria linhas novas com o mesmo `grupo_parcela_id` e a cadeia de datas contínua
- [ ] Diminuir o total remove as linhas finais e atualiza `parcela_total` das restantes
- [ ] Total < parcela atual → `400`; grupo de outro usuário → `404`
- [ ] Grupo com pendente vencida continua listado em `/api/parcelas-ativas`

### RF-02 · Criar novo parcelamento pelo dashboard

Botão **"+ Novo parcelamento"** na seção "Parcelas em andamento" abre um modal com:
título, valor da parcela, total de parcelas (≥ 2), parcela atual (default 1, permite
cadastrar parcelamento já em andamento), data de vencimento da próxima parcela,
categoria, forma de pagamento (default `CARTAO_CREDITO`) e responsável.

- Cria `parcela_total` linhas com um `grupo_parcela_id` novo (UUID), valor da parcela
  informado em todas (sem rateio de total), datas em cadeia mensal — a parcela atual
  recebe a data informada, as anteriores recuam e as seguintes avançam mês a mês.
- Linhas anteriores à parcela atual nascem `PAGO`; da atual em diante, `PENDENTE`.
- `tipo = GASTO`, `recorrente = FALSE`, `embedding = NULL`.

Endpoint novo: `POST /api/grupos` → `201`.

**Critérios de aceitação:**

- [ ] Criar 12x de R$ 100 gera 12 linhas com o mesmo `grupo_parcela_id` e valor 100.00 cada
- [ ] Parcela atual = 4 nasce com as linhas 1–3 `PAGO` e 4–12 `PENDENTE`
- [ ] O grupo criado aparece na seção "Parcelas em andamento" sem recarregar a página
- [ ] Total < 2, valor ≤ 0 ou campos obrigatórios ausentes → `400`

### RF-03 · Seção "Gastos fixos" no dashboard

Nova seção no dashboard (abaixo de "Parcelas em andamento") listando as transações do
usuário com `recorrente = TRUE`, ordenadas por dia de vencimento. Cada item exibe:
título, valor mensal, dia de vencimento (dia de `data`), categoria, forma de pagamento
e ações **Editar** / **Remover**; a seção tem o botão **"+ Novo gasto fixo"** e exibe o
**total mensal** somado dos itens.

Endpoint novo: `GET /api/gastos-fixos`.

**Critérios de aceitação:**

- [ ] A seção lista somente transações `recorrente = TRUE` do usuário autenticado
- [ ] Exibe título, valor, dia de vencimento, categoria e forma de pagamento de cada item
- [ ] Exibe o total mensal (soma dos valores, aritmética em `Decimal` no backend)
- [ ] Lista vazia mostra "Nenhum gasto fixo cadastrado"

### RF-04 · CRUD de gastos fixos

Sobre as mesmas linhas `recorrente = TRUE` (sem tabela nova):

- **Incluir** (`POST /api/gastos-fixos`): título, valor, data de início/vencimento,
  categoria (default `GASTOS_FIXOS`), forma de pagamento e responsável. Grava
  `recorrente = TRUE`, `parcela_numero = parcela_total = 1`, `grupo_parcela_id` novo,
  `tipo = GASTO`, `embedding = NULL`; status segue a regra existente do cadastro
  (PIX → `PAGO`; demais → `PENDENTE`).
- **Editar** (`PUT /api/gastos-fixos/{id}`): altera título, valor, data, categoria,
  forma de pagamento e responsável. `404` se não existir, não for do usuário ou não
  for `recorrente = TRUE`.
- **Remover** (`DELETE /api/gastos-fixos/{id}`): hard delete da linha (padrão do
  projeto); o gasto deixa de contar na projeção. Confirmação no frontend antes de
  excluir. Mesmas regras de `404`.

**Critérios de aceitação:**

- [ ] Incluir cria transação `recorrente = TRUE` 1/1 que aparece na seção e na projeção
- [ ] Editar valor/título/dia reflete na listagem após salvar
- [ ] Remover exclui a linha e some da seção e da projeção
- [ ] `PUT`/`DELETE` em transação não-recorrente ou de outro usuário → `404`
- [ ] Valor ≤ 0 ou campos obrigatórios ausentes no `POST` → `400`

### RF-05 · Proxy do frontend

Toda rota nova do backend ganha rota equivalente no `api_proxy` do Flask e método no
cliente HTTP de `frontend/services`, seguindo o padrão existente (repassa status e
corpo; `502` quando o backend está indisponível).

**Critérios de aceitação:**

- [ ] `PUT/POST /api/grupos*` e `GET/POST/PUT/DELETE /api/gastos-fixos*` funcionam via Flask
- [ ] Backend fora do ar → `502 {"erro": "backend indisponível"}`

---

## Decisões

- **Valor ao mudar o total de parcelas:** o formulário de edição expõe o valor da
  parcela; mudar o total cria/remove linhas com esse valor. Não há redistribuição de
  valor total (escolha do usuário em 12/06/2026).
- **"Incluir novas" parcelas:** significa criar um **novo grupo** de parcelamento pelo
  dashboard; estender grupo existente já é coberto pela edição do total (RF-01).
- **Gastos fixos = flag `recorrente`:** sem tabela própria; CRUD direto nas transações
  `recorrente = TRUE`, integrado ao que o agente já grava.
- **Recálculo de datas:** cadeia mensal (+1 mês preservando o dia, ajustando para o
  último dia do mês em meses curtos). O agente usa +30 dias na criação via WhatsApp;
  essa divergência é aceita — o dashboard passa a ser a ferramenta de correção.
- **Pendentes vencidas:** `listar_ativas` deixa de cortar em `hoje` para não esconder
  grupos com parcela atrasada/editada para o passado.

## Mudanças de dados

Nenhuma migração: usa colunas existentes (`recorrente`, `grupo_parcela_id`,
`parcela_numero`, `parcela_total`). Apenas novos endpoints, services e UI.

---

## Como verificar

| Requisito | Verificação |
|---|---|
| RF-01 | Testes do service de grupo: título/valor/data/atual/total, atomicidade, 400/404, pendente vencida listada |
| RF-02 | Teste do service de criação: 12 linhas, mesmo grupo, status por parcela atual, validações |
| RF-03 | Teste do endpoint `GET /api/gastos-fixos`: filtro `recorrente`, isolamento por usuário, total em `Decimal` |
| RF-04 | Testes de POST/PUT/DELETE: flag gravada, 404 para não-recorrente/outro usuário, validações |
| RF-05 | Testes do proxy Flask com cliente mockado (padrão dos testes existentes do frontend) |

Suíte: `uv run pytest tests/ -v` (mocks, sem DB/LLM reais — padrão do projeto).
