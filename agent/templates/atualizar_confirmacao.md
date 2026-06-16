✏️ *Confirme a atualização:*

*{{ registro.descricao }}*
{{ campo_valor_fmt }}
{{ campo_data_fmt }}
{{ campo_categoria_fmt }}
{{ campo_forma_fmt }}
{{ campo_responsavel_fmt }}
{{ campo_status_fmt }}
{% if parcelas_afetadas %}
📅 Parcelas afetadas: {{ parcelas_afetadas | join(' · ') }}
{% endif %}

_Responda *confirmar* para salvar ou *cancelar* para descartar._