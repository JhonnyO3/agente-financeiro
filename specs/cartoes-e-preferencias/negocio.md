# Negócio: Cartões de Crédito e Perfil/Preferências

**Status:** Rascunho para aprovação
**Feature:** cartoes-e-preferencias
**Escopo:** duas funcionalidades novas no painel (não são correções)

Duas features independentes, agrupadas por serem ambas "novas". Podem ser aprovadas e
executadas separadamente. O "como" técnico está em [`spec.md`](spec.md).

---

## Feature 5 — Cadastro de cartões de crédito

**Objetivo.** Permitir registrar **mais de um cartão** e vincular gastos e parcelamentos a um
cartão específico, para organizar as despesas por cartão.

**Motivação.** Hoje a transação só tem `forma_pagamento = CARTAO_CREDITO`, sem distinguir
qual cartão. Quem tem vários cartões não consegue ver "quanto está comprometido no cartão X"
nem organizar as parcelas por cartão.

**Atores.** Usuário autenticado (dono dos próprios cartões).

**Relacionamentos (importante).**
- **1 usuário → N cartões.** Cada cartão pertence a um único usuário (isolamento).
- **1 cartão → N transações.** Uma transação pertence a no máximo um cartão (opcional/pode
  ficar sem cartão). O parcelamento inteiro (grupo) segue o mesmo cartão.

**Regras de negócio.**
- Cartão tem: **apelido/nome** (ex.: "Nubank", "Inter Black") — obrigatório. Opcionais: dia
  de fechamento, dia de vencimento, cor (para o card no UI). **Não** guardamos bandeira,
  últimos 4 dígitos nem limite.
- Uma transação/parcelamento pode ser **vinculada a um cartão** (opcional). Faz sentido
  quando `forma_pagamento` é cartão, mas não deve travar o cadastro.
- Excluir um cartão **não pode apagar** as transações vinculadas — elas ficam sem cartão
  (desvinculadas), nunca deletadas.

**Capacidades-chave (o coração da feature).**
1. **Listar os gastos de um cartão** — ver todas as transações vinculadas àquele cartão.
2. **Filtrar os parcelamentos daquele cartão** — ver só os parcelamentos (grupos) do cartão.
3. **Vincular gastos "soltos" a um cartão** — pegar transações que hoje estão sem cartão e
   associá-las a um cartão (idealmente em lote), para organizar o histórico existente.

**O que o usuário vê.**
- Uma tela para **gerenciar cartões** (criar, editar, excluir).
- No cadastro/edição de transação e de parcelamento, poder **escolher o cartão**.
- Uma visão por cartão: total comprometido, parcelas em aberto e a **lista de gastos** do
  cartão, com filtro de parcelamentos.
- Uma forma de **atribuir gastos soltos** a um cartão.

**Critérios de aceite.**
- Consigo cadastrar 2+ cartões e vê-los listados.
- Consigo vincular um gasto e um parcelamento a um cartão específico.
- Consigo abrir um cartão e **ver a lista dos seus gastos** e **filtrar os parcelamentos** dele.
- Consigo selecionar gastos sem cartão e **vinculá-los** a um cartão.
- Consigo ver, por cartão, o total do mês e as parcelas em aberto.
- Excluir um cartão mantém as transações (apenas desvinculadas).
- Cada usuário só vê e mexe nos próprios cartões.

**Em aberto (decidir na aprovação).**
- O agente de WhatsApp deve passar a perguntar/registrar o cartão? (sugestão: **fora do
  escopo desta feature**; só o dashboard por ora.)
- "Fatura" por ciclo de fechamento (usando dia de fechamento) agora, ou basta o total por
  mês-calendário nesta primeira versão? (sugestão: **mês-calendário** agora.)

---

## Feature 6 — Página de Perfil/Preferências com metas de distribuição

**Objetivo.** O usuário define a **renda fixa** e uma **distribuição-alvo** por categoria
(ex.: 20% alimentação, 30% investimentos, …) e a página principal mostra, de forma gráfica,
**o quanto ele está aderente** a essa meta.

**Motivação.** Falta um referencial. Hoje o painel mostra o que foi gasto, mas não compara
com um plano/orçamento pessoal.

**Atores.** Usuário autenticado (as preferências são dele).

**Regras de negócio (decisões fechadas).**
- Cada usuário tem **uma** configuração de preferências.
- Campos: **renda mensal** (valor fixo, informativo) e um conjunto de **metas por categoria**
  em percentual. Categorias = as já existentes
  (ALIMENTACAO, TRANSPORTE, LAZER, EDUCACAO, GASTOS_FIXOS, COMPRAS, GASTOS_PONTUAIS,
  INVESTIMENTO).
- **Soma das metas ≤ 100%** — o máximo é 100% (a sobra representa folga/livre). Rejeitar/avisar
  se passar de 100%.
- **Aderência = % do total** (realizado): para cada categoria, `realizado_% = valor da
  categoria ÷ total de saídas do período`. Onde **total de saídas = gastos + investimentos**
  do período (assim a meta de "% em investimentos" também é medível). Comparado com a meta_%.
- **Janela = mês atual** (default).
- Preferências são opcionais: sem configuração, o painel funciona como hoje (sem o bloco de
  aderência).

**O que o usuário vê.**
- Uma página de **Perfil/Preferências** para definir renda e os percentuais por categoria,
  com indicador da soma (não pode passar de 100%).
- Na página principal, um bloco gráfico de **aderência**: meta vs. realizado por categoria,
  deixando claro onde está acima (estourou) e abaixo (folga) da meta.

**Critérios de aceite.**
- Consigo salvar minha renda e os percentuais por categoria.
- O sistema não deixa a soma passar de 100% e me avisa.
- A página principal mostra, quando há preferências, meta × realizado por categoria (realizado
  como % do total de saídas do mês).
- Fica claro onde estou acima da meta e onde estou abaixo.
- Cada usuário vê só as próprias preferências.

---

## Fora de escopo

- Correções do dashboard (gráfico, parcelas, projeção, transações) — spec
  `correcoes-dashboard`.
- Integração das duas features com o agente de WhatsApp.
- Orçamento por envelope, alertas/notificações automáticas, metas por mês variável.
- Fatura por ciclo de fechamento de cartão (fica para uma iteração futura).
