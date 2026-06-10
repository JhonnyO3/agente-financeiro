# Spec: Melhorias de Negócio — Parcelas, Status, Receitas e Projeção

**Status:** Aprovado
**Feature:** melhorias-dashboard
**Origem:** `specs/melhorias-dashboard/negocio.md` (RN-01 a RN-07)

## Contexto

O agente registra gastos/investimentos via WhatsApp e o dashboard Flask exibe e gerencia
os dados. Sete regras de negócio novas exigem evolução do modelo de dados (status,
responsável, forma de pagamento, detalhes), do agente (receitas, parcela atual,
enriquecimento de descrição) e do dashboard (visão de projeção futura, novos campos).

Mapeamento de nomenclatura negócio → código (decisão para minimizar churn):

| Negócio | Código | Observação |
|---|---|---|
| Nome (curto) | `descricao` (existente) | Já é curto; usado no embedding e formatação |
| Descrição (enriquecida) | `detalhes` (novo, TEXT nullable) | Preenchido pela IA com o contexto extra do usuário |

---

## Fora de Escopo

- Autenticação/multiusuário real — `responsavel` é texto livre, sem login
- Recorrências automáticas (assinaturas que se renovam sozinhas)
- Conciliação bancária / importação de extrato
- Notificações de vencimento de parcela
- Recálculo de embeddings dos registros existentes (texto do embedding não muda)
- Alterar a UX geral do dashboard além das seções/colunas descritas aqui

---

## Requisitos Funcionais

### RF-01 · Evolução do modelo de dados

Novas colunas em `transacoes` (migration Alembic, sem quebrar dados existentes):

| Coluna | Tipo | Regra |
|---|---|---|
| `status` | String NOT NULL | `PAGO` \| `PENDENTE` — default de coluna `PENDENTE` |
| `forma_pagamento` | String NOT NULL | `PIX` \| `CARTAO` \| `OUTRO` — default de coluna `OUTRO` |
| `responsavel` | String NOT NULL | default de coluna `Jhonatas` |
| `detalhes` | TEXT NULL | texto enriquecido pela IA (RF-05) |

Novos valores de enum (colunas são `String`, sem migration de tipo):

- `TipoEnum`: + `RECEITA` (mantém `GASTO` e `INVESTIMENTO`)
- `CategoriaEnum`: + `RECEITA`, + `PARCELAMENTOS` (`OUTROS` já existe)

Para registros existentes, a migration aplica: `status = PAGO` quando `data < hoje`,
senão `PENDENTE`; `forma_pagamento = OUTRO`; `responsavel = 'Jhonatas'`.

**Critérios de aceitação:**

- [ ] `alembic upgrade head` roda sem erro em banco com dados existentes
- [ ] Registros antigos com `data < hoje` ficam `PAGO`; futuros ficam `PENDENTE`
- [ ] `alembic downgrade -1` remove as colunas sem perder os dados originais

---

### RF-02 · Parcelamento com parcela atual e dia de vencimento (RN-01)

Quando o usuário informa um gasto parcelado com parcela atual (ex.: "2/4"), o sistema
gera **todas** as parcelas do grupo (1..N), não apenas as a partir da informada:

- Parcelas com `data < hoje` → `status = PAGO` (histórico)
- Parcelas com `data >= hoje` → `status = PENDENTE`
- O **dia de vencimento é preservado** mês a mês (10/06 → 10/07 → 10/08), substituindo
  a regra atual de `+30 dias`. Quando o dia não existe no mês (31/01 → fev), usa o
  último dia do mês
- A data informada refere-se à parcela atual; as anteriores retrocedem meses, as
  seguintes avançam
- Transações com `parcela_total > 1` recebem `categoria = PARCELAMENTOS`
  automaticamente (sobrescreve o categorizador)
- Sem parcela atual informada (ex.: "6x de 150"), assume parcela atual = 1
  (comportamento atual preservado)

Exemplo: entrada em 10/06/2026, "jogo batman play 5, R$ 200, parcela 2/4" gera:

| Data | descricao | Categoria | Valor | Parcela | Status |
|---|---|---|---|---|---|
| 10/05/2026 | jogo batman play 5 | PARCELAMENTOS | 200.00 | 1/4 | PAGO |
| 10/06/2026 | jogo batman play 5 | PARCELAMENTOS | 200.00 | 2/4 | PENDENTE |
| 10/07/2026 | jogo batman play 5 | PARCELAMENTOS | 200.00 | 3/4 | PENDENTE |
| 10/08/2026 | jogo batman play 5 | PARCELAMENTOS | 200.00 | 4/4 | PENDENTE |

Quando o usuário informa o **valor da parcela** (como acima), cada registro recebe esse
valor; quando informa o **valor total** ("900 em 6x"), divide com `Decimal` e a última
parcela absorve o resto (regra atual). A extração diferencia os dois casos.

**Critérios de aceitação:**

- [ ] "parcela 2/4" gera 4 registros no mesmo `grupo_parcela_id`
- [ ] Parcelas passadas nascem `PAGO`, atuais/futuras `PENDENTE`
- [ ] Dia do mês preservado; 31/01 + 1 mês = 28/02 (ou 29 em bissexto)
- [ ] Grupo parcelado recebe categoria `PARCELAMENTOS`
- [ ] Cadastro sem parcela atual continua funcionando como hoje

---

### RF-03 · Status de pagamento (RN-02)

- Extração captura a forma de pagamento quando mencionada ("paguei no pix" → `PIX`;
  "no cartão" → `CARTAO`; ausente → `OUTRO`)
- `forma_pagamento = PIX` → `status = PAGO` automático no cadastro
- Demais formas → `PENDENTE` (exceto parcelas passadas do RF-02, que nascem `PAGO`)
- Atualização de status:
  - **Dashboard**: campo status no modal de edição (`PUT /api/transacoes/<id>`)
  - **WhatsApp**: "paguei o jogo do batman" → busca semântica + confirmação
    (fluxo análogo ao ALTERAR existente) → `status = PAGO`

**Critérios de aceitação:**

- [ ] Cadastro mencionando PIX grava `forma_pagamento=PIX, status=PAGO`
- [ ] Cadastro no cartão grava `forma_pagamento=CARTAO, status=PENDENTE`
- [ ] PUT no dashboard altera o status
- [ ] "paguei X" via WhatsApp pede confirmação e marca PAGO

---

### RF-04 · Campo Responsável (RN-03)

- Extração captura o responsável quando mencionado ("minha mãe comprou..." →
  `responsavel = "Mãe"`); ausente → `"Jhonatas"`
- Dashboard exibe a coluna Responsável na tabela e o campo nos modais de edição/inclusão

**Critérios de aceitação:**

- [ ] Cadastro sem menção grava `responsavel = "Jhonatas"`
- [ ] Cadastro mencionando terceiro grava o nome capturado
- [ ] Coluna visível na tabela do dashboard; editável no modal

---

### RF-05 · Descrição enriquecida pela IA (RN-05)

- `descricao` (nome curto) continua como hoje — inclusive no texto do embedding
- Novo campo `detalhes`: a IA registra o contexto adicional que o usuário forneceu na
  mensagem ("comprei o jogo do batman na promoção da steam pra jogar com o pedro" →
  `descricao = "jogo batman"`, `detalhes = "Comprado na promoção da Steam, para jogar
  com o Pedro"`)
- Sem contexto extra → `detalhes = NULL`
- Dashboard mostra `detalhes` (tooltip ou linha expandida) e permite editar no modal

**Critérios de aceitação:**

- [ ] Mensagem com contexto extra preenche `detalhes`
- [ ] Mensagem seca ("gastei 50 no mercado") deixa `detalhes` NULL
- [ ] Embedding não inclui `detalhes` (formato atual inalterado)

---

### RF-06 · Receitas (RN-06)

- Novo tipo `RECEITA` com categoria `RECEITA` ("recebi meu salário de 5000" →
  `tipo=RECEITA, categoria=RECEITA, status=PAGO`)
- Receitas entram `status = PAGO` por padrão (dinheiro já recebido); receitas futuras
  agendadas entram `PENDENTE`
- Dashboard:
  - Novo card **Receitas** no resumo
  - Card **Saldo** passa a ser `receitas − gastos` (investimentos seguem em card próprio)
  - Filtro de tipo na tabela ganha a opção RECEITA
- Consultas via WhatsApp incluem receitas nos resumos (balanço do mês)

**Critérios de aceitação:**

- [ ] Cadastro de receita via WhatsApp e via dashboard (POST) funciona
- [ ] `/api/resumo` retorna `receitas` e `saldo = receitas − gastos`
- [ ] Resumo via WhatsApp mostra o balanço (receitas − gastos)

---

### RF-07 · Visão de projeção futura (RN-07)

Nova seção no dashboard com o comprometimento financeiro dos **próximos 6 meses**
(mês corrente + 5), alimentada por novo endpoint:

- `GET /api/projecao` → por mês: soma de gastos `PENDENTE`s, receitas `PENDENTE`s e
  saldo projetado, com a contagem de parcelas no mês
- Visão mensal (existente, seletor de período) permanece; a projeção é uma seção
  independente que ignora o seletor
- Gráfico de barras ou tabela compacta: um item por mês futuro

**Critérios de aceitação:**

- [ ] Projeção mostra exatamente 6 meses a partir do corrente
- [ ] Apenas lançamentos `PENDENTE` entram na projeção
- [ ] Parcela marcada como PAGA sai da projeção imediatamente (após reload)

---

### RF-08 · Backfill dos registros existentes (aceite da RN-01)

Script idempotente (`scripts/backfill_parcelas.py`, executado manualmente uma vez):

1. Varre grupos com `parcela_total > 1` cujo número de registros no grupo é menor
   que `parcela_total`
2. Cria as parcelas faltantes (anteriores e posteriores às existentes), preservando
   valor, descricao, categoria e embedding do grupo; datas derivadas do dia de
   vencimento da parcela existente; `status` por data (passada=PAGO, futura=PENDENTE)
3. Grupos ambíguos (registros do mesmo grupo com valores ou descrições divergentes)
   são **pulados e reportados**, nunca adivinhados
4. Imprime relatório: grupos completados, parcelas criadas, grupos pulados e por quê
5. `--dry-run` mostra o que seria feito sem gravar

**Critérios de aceitação:**

- [ ] Rodar duas vezes não duplica parcelas (idempotente)
- [ ] `--dry-run` não grava nada
- [ ] Grupos ambíguos aparecem no relatório e ficam intactos

---

### RF-09 · Dashboard atualizado para os novos campos

- Tabela de transações: colunas **Status** (badge PAGO verde / PENDENTE amarelo) e
  **Responsável**; novo filtro por status
- Modais de edição/inclusão: campos status, forma de pagamento, responsável e detalhes
- `GET/POST/PUT /api/transacoes` passam a aceitar/retornar os novos campos
- Cards de resumo: Gastos, **Receitas**, Investimentos, Saldo (`receitas − gastos`)

**Critérios de aceitação:**

- [ ] Filtro por status combina com os filtros existentes (tipo, categoria, período)
- [ ] POST manual com os novos campos persiste corretamente
- [ ] Badges de status visíveis na tabela

---

## Mudanças de API (contratos detalhados serão congelados em `contracts/`)

| Endpoint | Mudança |
|---|---|
| `GET /api/resumo` | + `"receitas"`; `"saldo"` passa a ser `receitas − gastos` |
| `GET /api/projecao` | **novo** — `[{mes, gastos_pendentes, receitas_pendentes, saldo_projetado, qtd_parcelas}]` |
| `GET /api/transacoes` | + campos `status, forma_pagamento, responsavel, detalhes` nos itens; + query param `status` |
| `POST /api/transacoes` | aceita os novos campos (todos opcionais, defaults da RF-01) |
| `PUT /api/transacoes/<id>` | aceita os novos campos |
| Demais endpoints | inalterados |

Valores monetários seguem como string decimal de 2 casas; cálculo só em Python/`Decimal`.

---

## Impacto no agente WhatsApp

| Componente | Mudança |
|---|---|
| Extrator (cadastro) | captura parcela atual, dia de vencimento, forma de pagamento, responsável, detalhes |
| Classificador | nova intenção de marcar pago ("paguei X") e cadastro de receita roteado para Cadastrar |
| Cadastrar | regras RF-02 (geração 1..N, dia preservado), RF-03 (status), categoria PARCELAMENTOS |
| Consultar | resumos incluem receitas e balanço |
| Formatador | respostas citam status e parcelas geradas |
| Prompts | `extracao.md`, `intencao.md`, `categorizacao.md` atualizados |

---

## Como Verificar

| Requisito | Como testar |
|---|---|
| RF-01 | `alembic upgrade head` em banco populado; conferir defaults por SELECT |
| RF-02 | WhatsApp: "comprei jogo batman 200 reais parcela 2/4 vence dia 10" → SELECT mostra 4 linhas, datas 10/05–10/08, status corretos |
| RF-03 | "paguei 50 no pix no mercado" → status PAGO; "no cartão" → PENDENTE; "paguei o batman" → confirmação → PAGO |
| RF-04 | "minha mãe gastou 80 no meu cartão na farmácia" → responsavel "Mãe" |
| RF-05 | Mensagem com contexto → detalhes preenchido; mensagem seca → NULL |
| RF-06 | "recebi salário 5000" → tipo RECEITA; card Receitas e Saldo no dashboard batem |
| RF-07 | Cadastrar parcelas futuras → projeção mostra 6 meses com somas corretas; marcar PAGO remove da projeção |
| RF-08 | Banco com grupo 2/4 incompleto → script cria 1,3,4; rodar de novo → 0 criações |
| RF-09 | Filtro status=PENDENTE + tipo=GASTO na tabela; POST manual com responsável customizado |

Todos os testes automatizados seguem o padrão do projeto: mocks, sem DB/LLM reais.
