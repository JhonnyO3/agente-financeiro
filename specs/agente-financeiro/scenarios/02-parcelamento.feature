Feature: Parcelamento
  Como usuário
  Quero registrar compras parceladas
  Para que cada parcela tenha seu próprio vencimento no banco

  Background:
    Given o número autorizado está configurado
    And o banco de dados está limpo

  Scenario: Cadastrar compra parcelada com valor por parcela
    When o usuário envia "comprei celular Samsung 6x de 150 reais"
    Then 6 transações são criadas no banco
    And todas têm o mesmo grupo_parcela_id
    And cada transação tem valor 150.00
    And cada transação tem parcela_total igual a 6
    And a parcela_numero vai de 1 a 6
    And a data de cada parcela é a anterior mais 30 dias

  Scenario: Cadastrar compra parcelada com valor total
    When o usuário envia "comprei TV 900 reais em 6x"
    Then 6 transações são criadas no banco
    And cada transação tem valor 150.00

  Scenario: Divisão com centavo é absorvida na última parcela
    When o usuário envia "comprei algo por 100 reais em 3x"
    Then 3 transações são criadas no banco
    And as parcelas 1 e 2 têm valor 33.33
    And a parcela 3 tem valor 33.34

  Scenario: Cartão sem parcelas dispara pergunta e aguarda resposta
    When o usuário envia "comprei geladeira no cartão 1500 reais"
    Then nenhuma transação é criada no banco
    And o agente pergunta "É à vista ou parcelado?"
    When o usuário responde "3 vezes"
    Then 3 transações são criadas no banco
    And cada transação tem valor 500.00

  Scenario: Consultar parcelas de uma compra específica
    Given existem 6 parcelas do "Celular Samsung" no banco
    When o usuário envia "parcelas do celular"
    Then a resposta lista as 6 parcelas
    And cada parcela exibe seu status (Paga, Próxima ou Futura)
