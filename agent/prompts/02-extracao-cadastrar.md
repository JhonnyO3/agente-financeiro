# Injection — Extração de Cadastro

Extraia os dados estruturados dos itens a cadastrar. O classificador já identificou a intenção; sua tarefa é preencher os campos com precisão.

## Parâmetros recebidos

{parametros}

## Regras de extração — Tipo

- GASTO para despesas
- INVESTIMENTO para aportes/aplicações
- RECEITA quando o usuário recebeu dinheiro: "recebi", "salário", "me pagaram", "caiu na conta"

## Regras de extração — Valores e parcelas

- parcela_atual: se o usuário indicar a parcela atual ("parcela 2/4", "2 de 4"), extraia o número. Ausente → parcela_atual=1
- Quando o usuário informa o valor DA PARCELA (ex.: "R$ 200, parcela 2/4"): valor_por_parcela=200, parcela_total=4, parcela_atual=2 e valor_total = valor_por_parcela × parcela_total
- Quando o usuário informa o valor TOTAL (ex.: "900 em 6x"): valor_total=900, parcela_total=6, valor_por_parcela=null, parcela_atual=1
- data_referencia é a data da parcela atual informada na mensagem
- Sem data informada → assumir hoje ({data_atual})
- Parcelas futuras: avançar o mesmo dia do mês, mês a mês

## Regras de extração — Forma de pagamento

- "paguei no pix", "fiz um pix" → PIX
- "no boleto" → BOLETO
- "no débito", "cartão de débito" → CARTAO_DEBITO
- "no cartão", "no crédito", "cartão de crédito" → CARTAO_CREDITO
- Qualquer compra parcelada / "em Nx" → sempre CARTAO_CREDITO
- Menção a cartão → CARTAO_CREDITO
- "dinheiro" → será mapeado para PIX pela Tool
- Forma não mencionada → PIX

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
