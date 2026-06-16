{% if multiplo %}
📋 *Confirme os registros abaixo:*
{% else %}
📋 *Confirme o registro abaixo:*
{% endif %}

{% for reg in registros %}
{% if multiplo %}
*{{ loop.index }}. {{ reg.descricao }}*
{% else %}
*{{ reg.descricao }}*
{% endif %}
{% if reg.parcela_total and reg.parcela_total > 1 %}
💰 Valor: {{ reg.parcela_total }}x de {{ reg.valor_fmt }} (total {{ reg.total_fmt }})
📅 Data: {{ reg.data_fmt }} (parcela {{ reg.parcela_numero }}/{{ reg.parcela_total }})
{% else %}
💰 Valor: {{ reg.valor_fmt }}
📅 Data: {{ reg.data_fmt }}
{% endif %}
🗂 Categoria: {{ reg.categoria }}
{% if reg.detalhes %}
💳 Pagamento: {{ reg.forma_pagamento }} _(detalhes: {{ reg.detalhes }})_
{% else %}
💳 Pagamento: {{ reg.forma_pagamento }}
{% endif %}
👤 Responsável: {{ reg.responsavel }}
📌 Status: {{ reg.status }}
{% if campos_faltantes %}
_(faltante: {{ campos_faltantes | join(', ') }})_
{% endif %}
{% if parcelas_futuras and not multiplo %}
📅 Parcelas: {{ parcelas_futuras | join(' · ') }}
{% endif %}

{% endfor %}
_Responda *confirmar* para salvar ou *cancelar* para descartar._