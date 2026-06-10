Feature: Consultar e Resumos Financeiros
  Como usuário
  Quero consultar meus gastos e investimentos
  Para tomar decisões financeiras informadas

  Background:
    Given o número autorizado está configurado
    And existem transações cadastradas no banco para junho/2026

  Scenario: Resumo mensal
    When o usuário envia "resumo de junho"
    Then a resposta contém total de gastos do mês de junho
    And a resposta contém breakdown por categoria
    And os valores são calculados em Python (não pelo LLM)

  Scenario: Resumo semanal
    When o usuário envia "quanto gastei essa semana"
    Then a resposta contém total de gastos de segunda a domingo da semana atual

  Scenario: Resumo geral — gastos vs investimentos
    When o usuário envia "resumo geral"
    Then a resposta contém total de gastos histórico
    And a resposta contém total de investimentos histórico

  Scenario: Resumo mensal não duplica parcelas
    Given existe uma compra parcelada em 6x com parcela em junho e demais nos meses seguintes
    When o usuário envia "resumo de junho"
    Then o total inclui apenas o valor da parcela de junho (não o total da compra)

  Scenario: Cálculo usa Decimal e não float
    Given existem 3 transações com valores 33.33, 33.33, 33.34
    When o usuário envia "resumo do mês"
    Then a resposta exibe total de 100.00 (sem erro de ponto flutuante)
