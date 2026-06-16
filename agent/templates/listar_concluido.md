📊 *Gastos de {{ periodo }}*

{% for grupo in grupos %}
*{{ grupo.titulo }}*
{% for item in grupo.itens %}
  • {{ item.descricao }} — {{ item.valor_fmt }} — {{ item.data_fmt }} — {{ item.emoji }} {{ item.status }}
{% endfor %}
_Subtotal: {{ grupo.subtotal_fmt }}_

{% endfor %}
💳 *Total do período: {{ total_fmt }}*
{% if pendente_positivo %}
⏳ *Pendente: {{ pendente_fmt }}*
{% endif %}
✅ *Pago: {{ pago_fmt }}*