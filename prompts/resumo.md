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
💰 Receitas R$ {total_receitas} · Gastos R$ {total_gastos} · Balanço R$ {balanco}   ← apenas quando houver receitas

*Por categoria:*
🍽️ Alimentação: R$ {valor}
🚗 Transporte: R$ {valor}
🎉 Lazer: R$ {valor}
🏠 Gastos fixos: R$ {valor}
🛍️ Compras: R$ {valor}
```

## Regras

- Quando houver receitas (`total_receitas` > 0), cite a linha de balanço no formato
  "Receitas R$ X · Gastos R$ Y · Balanço R$ Z", usando exatamente os valores de
  `total_receitas`, `total_gastos` e `balanco` fornecidos
- Sem receitas (`total_receitas` = 0), omita a linha de receitas/balanço
- Omita categorias com valor R$ 0,00
- Destaque o maior gasto do período
- Para filtros dinâmicos, adapte o título e as seções conforme o dado fornecido
- Mantenha o texto curto — WhatsApp não é um relatório PDF
