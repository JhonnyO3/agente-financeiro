# Prompt: Confirmação de Cadastro

Use quando um lançamento (simples ou parcelado) foi salvo com sucesso no banco.
Os dados já foram calculados em Python — não recalcule nada.

## Instrução

Formate a confirmação de cadastro de forma clara e concisa para WhatsApp.

## Formato para lançamento simples (parcela_total = 1)

```
✅ Registrado!

📅 {data}
💰 R$ {valor}
🏷️ {categoria}
📝 {descricao}
```

## Formato para lançamento parcelado (parcela_total > 1)

```
✅ Registrado em {parcela_total}x!

💰 {parcela_total}x de R$ {valor_por_parcela} (total R$ {valor_total})
🏷️ {categoria}
📝 {descricao}
📅 Parcelas: {lista_meses}
```

Onde `lista_meses` é gerada em Python no formato: `jun/26 · jul/26 · ago/26 ...`

## Regras

- Nunca exibir o `grupo_parcela_id`
- Omitir a linha de `descricao` se ela for vazia/None
- Manter resposta curta — sem texto adicional além do template
