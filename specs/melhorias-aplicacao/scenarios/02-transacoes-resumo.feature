# language: pt
Funcionalidade: Backend de transações e resumo
  RF-01 (paridade de contrato com o dashboard atual).

  Cenário: Resumo preserva o formato atual
    Dado transações do mês corrente
    Quando faço GET em /api/resumo?periodo=mes_atual
    Então recebo {gastos, receitas, investimentos, saldo, periodo} com valores em string

  Cenário: Criação assume PIX quando forma ausente
    Quando faço POST em /api/transacoes sem forma_pagamento
    Então a transação é criada com forma_pagamento "PIX"

  Cenário: Forma de pagamento inválida é rejeitada
    Quando faço POST em /api/transacoes com forma_pagamento "DINHEIRO"
    Então recebo status 400

  Cenário: Categorias só de gastos
    Dado gastos e investimentos no período
    Quando faço GET em /api/grafico/categorias
    Então apenas categorias de GASTO aparecem, com total e percentual
