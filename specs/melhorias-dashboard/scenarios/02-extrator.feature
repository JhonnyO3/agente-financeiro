# language: pt
# Tarefa: T02 — pytest (LLM mockado)
Funcionalidade: Extração v2

  Cenário: Retrocompatibilidade dos defaults
    Quando o LLM retorna apenas os campos antigos
    Então parcela_atual=1, forma_pagamento=OUTRO, responsavel="Jhonatas", detalhes=None

  Cenário: Parcela atual e valor por parcela
    Quando o LLM retorna valor_por_parcela=200, parcela_total=4, parcela_atual=2
    Então o modelo valida e expõe os três campos

  Cenário: Tipo receita aceito
    Quando o LLM retorna tipo="RECEITA"
    Então o modelo valida sem erro
