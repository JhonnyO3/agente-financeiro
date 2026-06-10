# Prompt: Categorização de Lançamento

Dado o contexto do lançamento, escolha a categoria mais adequada da lista predefinida.
Retorne apenas o JSON — sem explicação adicional.

## Categorias disponíveis

| Categoria    | Exemplos de uso                                              |
|--------------|--------------------------------------------------------------|
| ALIMENTACAO  | mercado, restaurante, lanche, delivery, padaria              |
| TRANSPORTE   | uber, combustível, passagem, estacionamento, manutenção carro|
| LAZER        | cinema, show, viagem, assinatura streaming, hobby            |
| INVESTIMENTO | ações, FIIs, CDB, tesouro direto, cripto                     |
| GASTOS_FIXOS | aluguel, internet, energia, água, plano de saúde, academia   |
| COMPRAS      | roupa, eletrônico, móvel, presente, farmácia                 |

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
