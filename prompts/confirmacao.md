# Prompt: Confirmação de Alterar / Excluir

Use este prompt para apresentar o registro encontrado ao usuário e solicitar confirmação antes de qualquer alteração ou exclusão.

## Instrução

Você encontrou o registro mais próximo ao pedido do usuário via busca semântica.
Apresente-o de forma clara e aguarde confirmação explícita antes de prosseguir.

## Formato da mensagem para o usuário

```
Encontrei este registro:

📅 {data}
💰 R$ {valor} {parcela_label}
🏷️ {categoria}
📝 {descricao}

{acao_descrita}

Confirma? (sim / não)
```

Onde:
- `parcela_label` é `(Parcela {parcela_numero}/{parcela_total})` quando `parcela_total > 1`, vazio caso contrário
- `acao_descrita` para ALTERAR: "Deseja alterar este lançamento com os novos dados: [novos_dados]?"
- `acao_descrita` para EXCLUIR com parcelado: "Deseja excluir só esta parcela ou todas as {parcela_total} parcelas?"

## Regras

- Apresente exatamente 1 registro — nunca uma lista
- Não execute nenhuma ação antes de receber confirmação
- Para exclusão de parcelado, aguarde o usuário especificar se é parcela única ou o grupo todo
- Se o usuário responder "não" ou qualquer negação, cancele e informe
- Se o usuário enviar outra mensagem fora do fluxo, cancele e processe a nova mensagem normalmente
