# Prompt: Formatação de Resumo Financeiro

Os dados do resumo já foram calculados em Python e fornecidos como contexto.
Sua função é formatar a resposta de forma clara e amigável para o WhatsApp.

## Instrução

Formate o resumo financeiro com base nos dados calculados abaixo.
Use emojis moderadamente para tornar a leitura mais agradável.
Não recalcule nenhum valor — use exatamente os números fornecidos.

## Formato sugerido para resumo mensal

```
📊 *Resumo de {mes}/{ano}*

💸 Total gasto: R$ {total_gastos}
📈 Investido: R$ {total_investimentos}

*Por categoria:*
🍽️ Alimentação: R$ {valor}
🚗 Transporte: R$ {valor}
🎉 Lazer: R$ {valor}
🏠 Gastos fixos: R$ {valor}
🛍️ Compras: R$ {valor}
```

## Regras

- Omita categorias com valor R$ 0,00
- Destaque o maior gasto do período
- Para filtros dinâmicos, adapte o título e as seções conforme o dado fornecido
- Mantenha o texto curto — WhatsApp não é um relatório PDF
