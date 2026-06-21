# Injection — Extração de Cadastro

Extraia os dados estruturados dos itens a cadastrar. O classificador já identificou a intenção; sua tarefa é preencher os campos com precisão.

## Mensagem do usuário

{mensagem}

## Parâmetros parciais (pode estar vazio se for a primeira extração)

{parametros}

## Uso do histórico

O campo `historico_recente` contém as mensagens anteriores desta conversa.

**Regra:** se `forma_pagamento`, `dia_vencimento` ou `parcelas` foram mencionados em mensagens anteriores, use esses valores — não peça de novo.

Exemplos de extração cross-turno:
- Turno 1: "comprei roupa" (sem forma) / Turno 2: "foi no crédito" → `forma_pagamento=CARTAO_CREDITO` com base no histórico
- Turno 1: "gastei 300" / Turno 2: "em 3x" → `total_parcelas=3, parcela_atual=1`
- Turno 1: "comprei algo que vence dia 10" / Turno 2: confirma valor → use `dia_vencimento=10` do histórico

## Regras de extração — Tipo

O campo `tipo` aceita EXATAMENTE um destes três valores — nunca use nomes de categoria aqui:

- `GASTO` — qualquer despesa, compra, pagamento ou gasto (inclui luminária, roupa, mercado, conserto…)
- `INVESTIMENTO` — aportes e aplicações financeiras
- `RECEITA` — quando o usuário recebeu dinheiro: "recebi", "salário", "me pagaram", "caiu na conta"

> ⚠️ `GASTOS_PONTUAIS`, `GASTOS_FIXOS`, `COMPRAS` etc. são valores de **categoria**, nunca de **tipo**.

## Regras de extração — Valores e parcelas

- **valor** = sempre o valor TOTAL da compra (número puro, sem moeda, sem símbolo, sem cálculos).
  - "5x de 300" → valor=1500 (300×5), total_parcelas=5, parcela_atual=1
  - "900 em 6x" → valor=900, total_parcelas=6, parcela_atual=1
  - "parcela 2/4 de 200" → valor=800 (200×4), total_parcelas=4, parcela_atual=2
- **parcela_atual**: só preencha se o usuário mencionar a parcela atual explicitamente ("parcela 2/4", "2ª de 5x"). Se não mencionar → null (não coloque 1 como default).
- **total_parcelas**: número total de parcelas quando o usuário mencionar parcelamento ("3x", "em 5 vezes"). Se não houver parcelamento → null.
- **dia_vencimento**: dia do mês de vencimento quando mencionado ("vence dia 10", "todo dia 5"). Ausente → null.
- Sem data informada → assumir hoje ({data_atual}).

## Regras de extração — Forma de pagamento

Inferir a forma com base no que o usuário comunicou sobre a transação:

- Menção a parcelas, "em Nx", "no crédito", vencimento futuro ("vence dia X", "dia X") → `CARTAO_CREDITO`
- "pix", "transferência", "à vista no débito", "cartão de débito" → `PIX` / `CARTAO_DEBITO`
- "no boleto" → `BOLETO`
- "dinheiro" → será mapeado para PIX pela Tool
- Nenhum contexto claro de forma → `forma_pagamento=null` (campo faltante, será perguntado)

> Interprete o sinal de pagamento que o usuário comunicou. Não faça mapeamento por nome de serviço, app ou banco.

## Regras de extração — Status

- Pagamento via PIX ou BOLETO → PAGO
- Parcela com vencimento passado ou hoje → PAGO
- Parcela com vencimento futuro → PENDENTE
- CARTAO_CREDITO sem data de vencimento → PENDENTE

## Regras de extração — Responsável

- Se a mensagem mencionar quem fez o lançamento, capture o nome
- Sem menção → usar {responsavel_padrao}

## Regras de extração — Descrição e detalhes

- descricao: nome curto do lançamento (ex.: "mercado", "notebook")
- detalhes: contexto extra além do essencial, em frase curta. Mensagem seca → null

## Categorização — decidir automaticamente

Ao extrair cada item, atribua a categoria conforme as regras abaixo:

| Categoria | Exemplos |
|---|---|
| ALIMENTACAO | mercado, restaurante, lanche, delivery, padaria |
| TRANSPORTE | uber, combustível, passagem, estacionamento, manutenção do carro |
| LAZER | cinema, show, viagem, hobby, parque |
| EDUCACAO | curso, mensalidade de ensino, faculdade, escola, material didático, idiomas |
| GASTOS_FIXOS | assinatura ou mensalidade recorrente: aluguel, internet, energia, água, plano de saúde, academia, streaming (Netflix, Spotify) |
| COMPRAS | bens de consumo e objetos: roupa, eletrônico, móvel, presente, acessórios |
| GASTOS_PONTUAIS | gasto único não-recorrente: conserto, reparo ou aquisição pontual da casa, taxa, multa, serviço avulso |

### Como decidir

- EDUCACAO: qualquer curso ou mensalidade de ensino é tipo=GASTO e categoria=EDUCACAO.
- GASTOS_FIXOS vs GASTOS_PONTUAIS: se é assinatura ou mensalidade que se repete → GASTOS_FIXOS. Se é gasto único que não se repete → GASTOS_PONTUAIS.
- GASTOS_PONTUAIS vs COMPRAS: objeto ou bem de consumo (roupa, eletrônico, presente) → COMPRAS. Serviço, reparo ou aquisição pontual ligada à manutenção → GASTOS_PONTUAIS.
- Se tipo=INVESTIMENTO → categoria=INVESTIMENTO (não consulte outras opções).
- Se tipo=RECEITA → categoria=RECEITA (não consulte outras opções).
- Nunca sugira OUTROS.
