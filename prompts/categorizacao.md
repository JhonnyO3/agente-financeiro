# Prompt: Categorização de Lançamento

Dado o contexto do lançamento, escolha a categoria mais adequada da lista predefinida.
Retorne apenas o JSON — sem explicação adicional.

## Categorias disponíveis

| Categoria    | Exemplos de uso                                              |
|--------------|--------------------------------------------------------------|
| ALIMENTACAO      | mercado, restaurante, lanche, delivery, padaria                    |
| TRANSPORTE       | uber, combustível, passagem, estacionamento, manutenção carro      |
| LAZER            | cinema, show, viagem, hobby, parque                                |
| INVESTIMENTO     | ações, FIIs, CDB, tesouro direto, cripto                          |
| GASTOS_FIXOS     | aluguel, internet, energia, água, plano de saúde, academia, assinatura recorrente (Netflix, Spotify, LinkedIn) |
| COMPRAS          | roupa, eletrônico, móvel, presente, farmácia, acessórios          |
| GASTOS_PONTUAIS  | gastos eventuais que não se repetem: conserto, taxa, multa, curso pontual, serviço avulso |
| OUTROS           | qualquer gasto que não se encaixa nas categorias acima             |

## Regra especial

Se `tipo = INVESTIMENTO`, a categoria é sempre `INVESTIMENTO` — não consulte outras opções.

## Saída esperada

```json
{
  "categoria": "ALIMENTACAO",
  "justificativa": "mercado → compra de alimentos"
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
