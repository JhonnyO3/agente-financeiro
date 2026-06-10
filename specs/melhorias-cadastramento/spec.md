# Spec: Melhorias de Cadastramento — Forma de Pagamento, Categorias, Recorrência

**Status:** Aprovado
**Feature:** melhorias-cadastramento
**Origem:** `specs/melhorias-cadastramento/negocio.md` + sessão de correção manual
(`dados-originais.txt` → `dados-corrigidos.txt`)

## Contexto

O agente registra transações via WhatsApp. Após corrigir a base registro a registro, o
usuário definiu regras novas para os próximos cadastros e uma migração para sanitizar os
dados existentes. As mudanças tocam o enum de `forma_pagamento`, o enum de `categoria`, o
fluxo de extração/cadastro do agente, e adicionam o conceito de **gasto recorrente**.

### Estado atual (código)

- `FormaPagamentoEnum`: `PIX` | `CARTAO` | `OUTRO` (default de coluna `OUTRO`)
- `CategoriaEnum`: `ALIMENTACAO`, `TRANSPORTE`, `LAZER`, `INVESTIMENTO`, `GASTOS_FIXOS`,
  `COMPRAS`, `GASTOS_PONTUAIS`, `OUTROS`, `RECEITA`, `PARCELAMENTOS`
- `Transacao.data`, `parcela_numero`, `parcela_total` são `NOT NULL`
- Parcelado força `categoria = PARCELAMENTOS` (`CadastrarService._processar`)
- Default de cadastro joga `forma_pagamento = OUTRO`

---

## Fora de Escopo

- Recorrência automática que gera lançamentos sozinha mês a mês (o flag `recorrente`
  apenas marca o registro; a projeção/cálculo mensal consome o flag, não cria linhas)
- Notificação de vencimento de fatura/parcela
- Conciliação bancária / importação de extrato
- Recálculo de embeddings dos registros migrados (texto do embedding não inclui valor,
  categoria muda mas o embedding não é refeito nesta entrega)
- Multiusuário / autenticação

---

## Requisitos Funcionais

### RF-01 · Enum de forma de pagamento

`FormaPagamentoEnum` passa a ser: `CARTAO_CREDITO`, `CARTAO_DEBITO`, `PIX`, `BOLETO`.

- `OUTRO` é **removido**. O valor `OUTRO` nunca deve ser gravado.
- Renomeação semântica `CARTAO` → `CARTAO_CREDITO`.

**Critérios de aceitação:**
- [ ] `FormaPagamentoEnum` contém exatamente os 4 valores acima
- [ ] Nenhum caminho de cadastro grava `OUTRO`
- [ ] Default de coluna deixa de ser `OUTRO`

### RF-02 · Regras de forma de pagamento no cadastro

- Forma não informada pelo usuário ⇒ assume `PIX`.
- Usuário indicou parcelas (`parcela_total > 1`) ⇒ `CARTAO_CREDITO`.

**Critérios de aceitação:**
- [ ] Mensagem sem forma explícita → registro com `PIX`
- [ ] Mensagem com parcelas → registro com `CARTAO_CREDITO`, mesmo sem o usuário citar cartão

### RF-03 · Status e data por forma de pagamento

- `PIX` ⇒ `status = PAGO`, `data` = data informada/real.
- `CARTAO_CREDITO` ⇒ `status = PENDENTE`, `data` deslocada para o vencimento da fatura.
- `CARTAO_DEBITO` ⇒ `status = PAGO`, data real (débito sai na hora).
- `BOLETO` ⇒ `status = PENDENTE`, data de vencimento.

> **Decisão:** a data da fatura é o **mesmo dia, mês seguinte** (`data + 1 mês`,
> preservando o dia), replicando o comportamento observado na correção (06-06 → 07-06).
> Não há dia de fechamento configurável por cartão nesta entrega.

**Critérios de aceitação:**
- [ ] PIX → `PAGO`; CARTAO_CREDITO → `PENDENTE`
- [ ] CARTAO_CREDITO desloca a data para a fatura
- [ ] À vista (PIX/DEBITO) mantém a data real

### RF-04 · Enum de categorias

`CategoriaEnum` final:

`ALIMENTACAO`, `TRANSPORTE`, `LAZER`, `EDUCACAO`, `GASTOS_FIXOS`, `COMPRAS`,
`GASTOS_PONTUAIS`, `INVESTIMENTO`, `RECEITA`.

- **Adiciona** `EDUCACAO`.
- **Remove** `PARCELAMENTOS` e `OUTROS`.
- Mantém `INVESTIMENTO` (para investimentos financeiros reais) e `RECEITA`.

**Critérios de aceitação:**
- [ ] `CategoriaEnum` contém exatamente os 9 valores acima
- [ ] `PARCELAMENTOS` e `OUTROS` não existem mais no enum

### RF-05 · Categoria herda a natureza da compra (fim de PARCELAMENTOS)

`CadastrarService._processar` deixa de forçar `PARCELAMENTOS` quando `parcela_total > 1`.
A categoria de um parcelamento é a categoria real do item, vinda do categorizador.

- Curso/educação ⇒ `categoria = EDUCACAO`, `tipo = GASTO`.
- Compra de bem físico/objeto ⇒ `COMPRAS` (ex.: pandora, jogo, celular, carro).
- Gasto único não-recorrente e não-consumo corriqueiro ⇒ `GASTOS_PONTUAIS`
  (ex.: aquecedor — reparo/aquisição pontual da casa).

**Critérios de aceitação:**
- [ ] Cadastro parcelado de curso → `EDUCACAO`, `tipo GASTO`
- [ ] Cadastro parcelado de objeto → `COMPRAS`
- [ ] Nenhum cadastro novo grava `PARCELAMENTOS`

### RF-06 · Gasto recorrente (GASTOS_FIXOS)

Nova coluna `recorrente BOOLEAN NOT NULL DEFAULT FALSE` em `transacoes`.

Fluxo do agente: ao classificar a transação como `GASTOS_FIXOS`, o agente **pergunta ao
usuário** se pode considerar esse gasto todos os meses (novo estado de confirmação no
pipeline, p.ex. `AGUARDAR_RECORRENCIA`).

- Confirmado ⇒ `recorrente = TRUE`, `parcela_numero = parcela_total = 1`,
  sem estrutura de parcela; entra na base de cálculo de todos os meses.
- Negado ⇒ `recorrente = FALSE`, registro pontual normal.

> `data` de um recorrente representa a data de início/referência (decisão de
> implementação: manter `data` preenchida com a data-base, em vez de torná-la nullable,
> para preservar a integridade e o histórico). A projeção mensal considera todo registro
> com `recorrente = TRUE` como ativo nos meses seguintes.

**Critérios de aceitação:**
- [ ] Classificação em `GASTOS_FIXOS` dispara a pergunta de recorrência
- [ ] Resposta afirmativa grava `recorrente = TRUE` sem parcelas
- [ ] `alembic upgrade head` adiciona `recorrente` com default `FALSE` sem quebrar dados
- [ ] `alembic downgrade -1` remove a coluna

### RF-07 · Valor por parcela

Cada registro de parcela guarda o valor **daquela parcela**, não o total. Quando o total
não divide exato, o resto é distribuído entre as parcelas (comportamento atual de
`_valores_das_parcelas` é mantido/validado).

**Critérios de aceitação:**
- [ ] Soma dos valores das parcelas = valor total informado
- [ ] Resto de divisão não exata é absorvido (sem centavo perdido)

### RF-08 · Migração de sanitização dos dados existentes

Migração de dados (Alembic data migration ou script idempotente) que aplica em
`transacoes` as correções do usuário, usando `dados-corrigidos.txt` como alvo. Regras:

1. `forma_pagamento`: converter `CARTAO` → `CARTAO_CREDITO`; todo `OUTRO` remanescente é
   resolvido pela regra do RF-02/RF-03 (parcelado → `CARTAO_CREDITO`; à vista → `PIX`).
   Nenhum `OUTRO` pode sobrar.
2. Recategorização conforme o arquivo corrigido:
   - asimov academy, curso claude code, curso de inglês → `EDUCACAO` (tipo `GASTO`)
   - jogo batman, pandora do Morumbi, parcela do carro, parcela do celular, Nubank → `COMPRAS`
   - parcela do aquecedor → `GASTOS_PONTUAIS` (tipo `GASTO`)
3. Recorrentes/assinaturas (academia, LinkedIn, Spotify) → `recorrente = TRUE`,
   `parcela_numero = parcela_total = 1`. Spotify, sendo assinatura, recebe
   `forma_pagamento = CARTAO_CREDITO` (não `OUTRO`). `uber` é à vista → `PIX`.
4. Valores corrigidos conforme o arquivo (ex.: aquecedor 633, celular 228, cuecas 174,
   carro 1200, Nubank 922, batman 74,9x).
5. Remover registros de teste: **Coxinha, Sorvete do Mac, tokens open ai, Claude code (472, OUTROS)**.
6. Inserir como recorrentes (`GASTOS_FIXOS`, `recorrente = TRUE`): **Google Drive (14,90)**
   e **Claude code Max (500)**.
7. `zara` (parcelas em `COMPRAS`) recebe um `grupo_parcela_id` próprio (UUID novo),
   desvinculado do grupo do batman.

**Critérios de aceitação:**
- [ ] Após a migração, nenhum registro tem `forma_pagamento = OUTRO`
- [ ] Nenhum registro tem `categoria` em (`PARCELAMENTOS`, `OUTROS`)
- [ ] academia, LinkedIn, Spotify, Google Drive, Claude code Max têm `recorrente = TRUE` e sem parcela
- [ ] Os 4 itens de teste foram removidos
- [ ] A migração é idempotente (rodar duas vezes não duplica nem corrompe)

---

## Decisões (antes em aberto)

- **Dia da fatura (RF-03):** mesmo dia, mês seguinte (`data + 1 mês`). Sem dia de
  fechamento configurável nesta entrega.
- **`zara` na migração:** tratar como item novo — gerar um `grupo_parcela_id` (UUID)
  próprio, desvinculando do grupo do batman.
- **Spotify/uber:** Spotify é assinatura → `recorrente = TRUE`, `CARTAO_CREDITO`. uber é
  à vista → `PIX`. Nenhum `OUTRO` permanece.

---

## Como verificar

| Requisito | Verificação |
|---|---|
| RF-01/RF-02 | Teste de pipeline: mensagem sem forma → PIX; com parcelas → CARTAO_CREDITO |
| RF-03 | Teste de cadastro: PIX=PAGO/data real; CARTAO_CREDITO=PENDENTE/data deslocada |
| RF-04 | Teste de enum: valores exatos; ausência de PARCELAMENTOS/OUTROS |
| RF-05 | Teste: curso parcelado → EDUCACAO/GASTO; objeto → COMPRAS; nenhum PARCELAMENTOS |
| RF-06 | Teste de pipeline do estado AGUARDAR_RECORRENCIA + migration up/down |
| RF-07 | Teste: soma das parcelas == total; sem perda de centavo |
| RF-08 | Teste da migração em base de fixture: invariantes do checklist acima |
