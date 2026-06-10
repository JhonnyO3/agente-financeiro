# language: pt
# Tarefa: T02 — testes automatizados (pytest, repository mockado)
Funcionalidade: API de resumo e pizza de categorias

  Cenário: Resumo soma por tipo com Decimal
    Dado transações no período: GASTO 100.00, GASTO 250.00, INVESTIMENTO 500.00
    Quando faço GET /api/resumo?periodo=mes_atual
    Então recebo gastos "350.00", investimentos "500.00" e saldo "150.00" como strings

  Cenário: Saldo negativo
    Dado transações no período: GASTO 600.00, INVESTIMENTO 100.00
    Quando faço GET /api/resumo
    Então o saldo é "-500.00"

  Cenário: Pizza exclui investimentos e categorias zeradas
    Dado transações: GASTO ALIMENTACAO 150.00, GASTO TRANSPORTE 100.00, INVESTIMENTO INVESTIMENTO 999.00
    Quando faço GET /api/grafico/categorias
    Então recebo apenas ALIMENTACAO e TRANSPORTE
    E os percentuais somam aproximadamente 100

  Cenário: Pizza ordenada por total decrescente
    Dado transações de gasto em 3 categorias com totais distintos
    Quando faço GET /api/grafico/categorias
    Então o array vem ordenado por total decrescente
