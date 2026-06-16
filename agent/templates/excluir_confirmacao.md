{% if modo == 'lote' %}
🗑️ *Confirme a exclusão:*

Você está prestes a excluir *{{ qtd }}* registros de *{{ periodo }}*.

_Responda *confirmar* para excluir ou *cancelar* para descartar._
{% else %}
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

_Responda *confirmar* para excluir ou *cancelar* para descartar._
{% endif %}