# Prompt: Categorização de Lançamento

Dado o contexto do lançamento, escolha a categoria mais adequada da lista predefinida.
Retorne apenas o JSON — sem explicação adicional.

## Categorias disponíveis

| Categoria       | Exemplos de uso                                                                 |
|-----------------|---------------------------------------------------------------------------------|
| ALIMENTACAO     | mercado, restaurante, lanche, delivery, padaria                                 |
| TRANSPORTE      | uber, combustível, passagem, estacionamento, manutenção do carro                |
| LAZER           | cinema, show, viagem, hobby, parque                                             |
| EDUCACAO        | curso, mensalidade de ensino, faculdade, escola, material didático, idiomas     |
| GASTOS_FIXOS    | assinatura ou mensalidade recorrente: aluguel, internet, energia, água, plano de saúde, academia, streaming (Netflix, Spotify) |
| COMPRAS         | bens de consumo e objetos: roupa, eletrônico, móvel, presente, acessórios       |
| GASTOS_PONTUAIS | gasto único não-recorrente: conserto, reparo ou aquisição pontual da casa (ex.: aquecedor), taxa, multa, serviço avulso |

## Como decidir

- **EDUCACAO**: qualquer curso ou mensalidade de ensino (inglês, faculdade, escola)
  é `tipo=GASTO` e `categoria=EDUCACAO`.
- **GASTOS_FIXOS** vs **GASTOS_PONTUAIS**: se é uma assinatura ou mensalidade que se
  repete todo período, é `GASTOS_FIXOS`. Se é um gasto único que não se repete
  (um conserto, um reparo, a aquisição pontual de um item para a casa), é `GASTOS_PONTUAIS`.
- **GASTOS_PONTUAIS** vs **COMPRAS**: um objeto ou bem de consumo (roupa, eletrônico,
  presente) é `COMPRAS`. Um serviço, reparo ou aquisição pontual ligada à manutenção
  da casa é `GASTOS_PONTUAIS`.

## Regra especial

Se `tipo = INVESTIMENTO`, a categoria é sempre `INVESTIMENTO` — não consulte outras opções.

## Categorias reservadas (NÃO retornar)

`INVESTIMENTO` e `RECEITA` são atribuídas automaticamente pelo sistema e **nunca** devem
ser retornadas por você. Nunca sugira `OUTROS`. Escolha sempre uma das categorias da tabela acima.

## Saída esperada

```json
{
  "categoria": "ALIMENTACAO"
}
```

## Entrada esperada

```json
{
  "tipo": "GASTO",
  "descricao": "mercado",
  "valor": 150.00
}
```
