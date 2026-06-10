# language: pt
Funcionalidade: Gráficos e projeção em janela de 13 meses
  RF-03, RF-05.

  Cenário: Mensal retorna 13 meses
    Dado transações em alguns meses
    Quando faço GET em /api/grafico/mensal
    Então a resposta tem 13 entradas, de 6 meses atrás a 6 à frente, em ordem crescente
    E meses sem dados aparecem com "0.00"

  Cenário: Evolução inclui a série de receitas
    Dado um mês com gastos, investimentos e receitas
    Quando faço GET em /api/grafico/evolucao
    Então cada entrada tem os campos gastos, investimentos e receitas
    E a resposta tem 13 entradas

  Cenário: Projeção soma todas as transações do mês
    Dado um mês futuro com uma parcela PAGA e uma PENDENTE
    Quando faço GET em /api/projecao
    Então o total do mês considera ambas (não filtra apenas PENDENTE)
    E a resposta cobre 13 meses
