🔍 Encontrei mais de um registro. Qual você quer {{ verbo }}?

{% for op in opcoes %}
{% if op.emoji %}
*{{ loop.index }}.* {{ op.descricao }} — {{ op.valor_fmt }} — {{ op.data_fmt }} — {{ op.emoji }} {{ op.status }}
{% else %}
*{{ loop.index }}.* {{ op.descricao }} — {{ op.valor_fmt }} — {{ op.data_fmt }} — {{ op.extra }}
{% endif %}
{% endfor %}

_Responda com o número do registro._