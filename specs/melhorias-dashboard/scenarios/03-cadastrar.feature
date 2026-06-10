# language: pt
# Tarefa: T03 — pytest (repository/embedder/extrator mockados)
Funcionalidade: Cadastro v2

  Cenário: Parcela 2/4 gera o grupo completo
    Dado extração com valor_por_parcela=200, parcela_total=4, parcela_atual=2, data=10/06/2026
    Quando executo o cadastro
    Então criar_lote recebe 4 itens no mesmo grupo, datas 10/05..10/08
    E a parcela 1 nasce PAGO e as demais PENDENTE
    E todas com categoria PARCELAMENTOS e valor 200.00

  Cenário: Valor total dividido (comportamento atual)
    Dado extração com valor_total=900, parcela_total=6, sem valor_por_parcela
    Quando executo o cadastro
    Então 6 parcelas de 150.00 com resto absorvido na última

  Cenário: PIX nasce pago
    Dado extração à vista com forma_pagamento=PIX
    Então o registro nasce status=PAGO

  Cenário: Receita força categoria e status
    Dado extração tipo=RECEITA, data=hoje
    Então categoria=RECEITA e status=PAGO, sem chamar o categorizador

  Cenário: Responsável e detalhes propagados
    Dado extração com responsavel="Mãe" e detalhes="promoção da Steam"
    Então o TransacaoCreate carrega ambos
