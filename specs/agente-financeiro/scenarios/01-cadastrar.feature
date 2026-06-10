Feature: Cadastrar Gasto/Investimento
  Como usuário autorizado
  Quero registrar gastos e investimentos via WhatsApp
  Para que minhas finanças fiquem organizadas no banco de dados

  Background:
    Given o número autorizado é "5511957818539"
    And o banco de dados está limpo

  Scenario: Cadastrar gasto simples sem data
    When o usuário envia "gastei 45 reais no mercado"
    Then 1 transação é criada no banco
    And a transação tem tipo "GASTO"
    And a transação tem valor 45.00
    And a transação tem categoria "ALIMENTACAO"
    And a transação tem data igual à data de hoje
    And a transação tem parcela_total igual a 1

  Scenario: Cadastrar investimento
    When o usuário envia "comprei PETR4 por 300 reais"
    Then 1 transação é criada no banco
    And a transação tem tipo "INVESTIMENTO"
    And a transação tem categoria "INVESTIMENTO"
    And a transação tem valor 300.00

  Scenario: Cadastrar gasto com data específica
    When o usuário envia "paguei 80 reais de uber ontem"
    Then 1 transação é criada no banco
    And a transação tem categoria "TRANSPORTE"
    And a transação tem data igual a ontem

  Scenario: Mensagem de número não autorizado é descartada
    Given uma mensagem do número "5511999999999"
    When o número não autorizado envia "gastei 100 reais"
    Then nenhuma transação é criada no banco
    And nenhuma resposta é enviada

  Scenario: Mencionar cartão dispara pergunta antes de salvar
    When o usuário envia "comprei um notebook no cartão por 3000 reais"
    Then nenhuma transação é criada no banco
    And o agente responde com pergunta sobre parcelas
