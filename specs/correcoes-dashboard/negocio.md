# Negócio: Correções e Melhorias do Dashboard

**Status:** Rascunho para aprovação
**Feature:** correcoes-dashboard
**Escopo:** ajustes em comportamento existente do painel React (sem features novas)

Reúne 4 correções/melhorias reportadas sobre telas que já existem. Cada item traz o
problema percebido, o comportamento esperado e critérios de aceite. O "como" técnico
está em [`spec.md`](spec.md).

---

## 1. Gráfico "Evolução Financeira" — proporção/escala

**Problema.** As três séries (Gastos, Receitas, Investimentos) dividem o mesmo eixo Y
linear. Como Investimentos chega a ~R$66k e Gastos ficam na casa de ~R$1k, a linha de
Gastos vira praticamente uma reta rente ao zero — fica impossível de enxergar a variação.

**Esperado.** Conseguir ler a evolução de todas as séries mesmo quando as magnitudes são
muito diferentes. Um gasto de R$1.000 não pode parecer uma linha reta.

**Critérios de aceite.**
- Com dados onde uma série é ~50× maior que outra, a série menor mostra variação visível
  mês a mês (não achatada no zero).
- Continua sendo possível comparar as séries e ler os valores (tooltip/eixo) sem ambiguidade.
- Legível em desktop e mobile.

---

## 2. "Parcelas Ativas" — exibir total

**Problema.** A seção lista os cartões/parcelamentos ativos, mas não mostra nenhum total
agregado. A seção "Assinaturas & Gastos Fixos" logo acima já mostra `N itens · R$X/mês`;
"Parcelas Ativas" não tem equivalente.

**Esperado.** Um resumo no cabeçalho da seção com os totais relevantes.

**Critérios de aceite.**
- O cabeçalho de "Parcelas Ativas" mostra a **quantidade** de parcelamentos ativos.
- Mostra o **total mensal** (soma do valor da próxima parcela de cada grupo).
- Mostra o **total restante** (soma de `parcelas_restantes × valor_parcela` de cada grupo).
- Os valores batem com a soma dos cards exibidos.

---

## 3. "Projeção 6 Meses" — o que está sendo considerado

**Problema.** Para o mês seguinte, somando gastos fixos + parcelas manualmente dá ~R$3k,
mas a Projeção mostra **R$1.691**. Faltam os gastos fixos.

**Diagnóstico (confirmado no banco real, ref. Jul/2026).**
- A Projeção soma **apenas transações já gravadas com data no mês futuro**. As parcelas
  viram linhas futuras reais, então entram; os **gastos fixos mensais não** — eles só
  existem como linha do mês corrente e nunca são projetados adiante.
- Ago/2026: 8 linhas de parcela = **R$1.691,24** (é o número exibido). Gastos fixos do mês
  (Claude Code, Curso de inglês, Total Pass, internet, LinkedIn, Spotify) = **R$1.303,90**,
  que somados às parcelas dão **~R$2.995 ≈ 3k** — exatamente a conta do usuário.
- O campo `recorrente` existe no modelo mas está `false` em **100%** da base — nada marca
  um gasto como recorrente hoje, e a Projeção ignora esse campo de qualquer forma.

**Esperado.** A projeção do mês futuro deve considerar **gastos fixos/recorrentes + receitas
recorrentes + parcelas**, não só as parcelas.

**Critérios de aceite.**
- A projeção de um mês futuro inclui os gastos fixos/recorrentes esperados para aquele mês.
- Inclui receitas recorrentes (ex.: salário) esperadas.
- Continua incluindo as parcelas já lançadas.
- O usuário consegue entender **como** cada mês foi projetado (transparência: o que é real
  vs. projetado).
- Regra explícita e documentada para o que conta como "recorrente" (ver decisão na spec).

---

## 4. Transações — filtro por mês e bulk update de status

**Problema A.** A tabela de Transações não tem um filtro de mês próprio com default no mês
atual — ela segue o seletor global de período usado pelos gráficos/KPIs, o que mistura os
contextos.

**Problema B.** Só dá para alterar o status (PAGO/PENDENTE) de uma transação por vez. Marcar
várias como pagas é repetitivo.

**Esperado.**
- Filtrar a tabela de Transações por mês, **começando no mês atual por padrão**.
- Selecionar várias linhas e alterar o status de todas de uma vez.

**Critérios de aceite.**
- Ao abrir o painel, a tabela de Transações já mostra o mês atual por default.
- Existe um controle para trocar o mês exibido na tabela.
- É possível selecionar múltiplas linhas (inclusive "selecionar todas as visíveis").
- Uma ação em lote altera o status das selecionadas para PAGO ou PENDENTE numa única
  operação, e a tabela reflete o resultado.
- A operação é atômica por requisição e respeita o isolamento por usuário.

---

## Fora de escopo

- Cadastro de cartões de crédito e página de preferências/metas — ver spec
  `cartoes-e-preferencias`.
- Mudanças no agente de WhatsApp e no pipeline de classificação.
- Redesenho visual amplo do dashboard (só os ajustes pontuais acima).
