✅ *Registrado com sucesso!*

{% if qtd == 1 and registros %}
{% set reg = registros[0] %}
{% if reg.parcela_total and reg.parcela_total > 1 %}
_{{ reg.descricao }}_ {{ reg.parcela_total }}x de *{{ reg.valor_fmt }}* foi salvo.
{% else %}
_{{ reg.descricao }}_ de *{{ reg.valor_fmt }}* foi salvo.
{% endif %}
{% else %}
*{{ qtd }} registros salvos:*
{% for reg in registros %}
  • {{ reg.descricao }} — {% if reg.parcela_total and reg.parcela_total > 1 %}{{ reg.parcela_total }}x de {{ reg.valor_fmt }}{% else %}{{ reg.valor_fmt }}{% endif %}
{% endfor %}
{% endif %}

Digite *extrato* para ver o resumo do mês. 📊