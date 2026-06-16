🗑️ *Confirme a exclusão:*

*{{ registro.descricao }}*
💰 Valor: {{ registro.valor_fmt }}
📅 Data: {{ registro.data_fmt }}
🗂 Categoria: {{ registro.categoria }}
{% if registro.detalhes %}
💳 Pagamento: {{ registro.forma_pagamento }} _(detalhes: {{ registro.detalhes }})_
{% else %}
💳 Pagamento: {{ registro.forma_pagamento }}
{% endif %}
👤 Responsável: {{ registro.responsavel }}
📌 Status: {{ registro.status }}

⚠️ Este registro possui parcelas futuras: {{ parcelas_futuras | join(' · ') }}
*1.* Somente este
*2.* Todos, incluindo as parcelas futuras
_Responda com o número — ou *cancelar*._