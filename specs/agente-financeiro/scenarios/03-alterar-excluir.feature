Feature: Alterar e Excluir Transações
  Como usuário
  Quero corrigir ou remover lançamentos incorretos
  Para manter meu histórico financeiro preciso

  Background:
    Given o número autorizado está configurado
    And existe uma transação de "mercado" com valor 45.00 cadastrada ontem

  Scenario: Alterar valor de uma transação via busca semântica
    When o usuário envia "muda o gasto do mercado de ontem para 60 reais"
    Then o agente exibe o registro encontrado
    And o agente solicita confirmação
    When o usuário responde "sim"
    Then a transação tem valor 60.00 no banco

  Scenario: Cancelar alteração respondendo não
    When o usuário envia "altera o gasto do mercado"
    Then o agente exibe o registro encontrado
    When o usuário responde "não"
    Then a transação mantém o valor original 45.00
    And o agente informa que a operação foi cancelada

  Scenario: Excluir uma transação simples com confirmação
    When o usuário envia "exclua o gasto do mercado de ontem"
    Then o agente exibe o registro encontrado
    And solicita confirmação de exclusão
    When o usuário responde "sim"
    Then a transação não existe mais no banco

  Scenario: Excluir uma parcela de um parcelado — apenas essa parcela
    Given existem 6 parcelas do "Celular Samsung" no banco
    When o usuário envia "exclua a parcela do celular de julho"
    Then o agente exibe o registro encontrado com "Parcela 2/6"
    And pergunta "Deseja excluir só esta parcela ou todas as 6 parcelas?"
    When o usuário responde "só essa"
    Then 1 transação é removida do banco
    And as outras 5 parcelas permanecem

  Scenario: Excluir todas as parcelas de um parcelado
    Given existem 6 parcelas do "Celular Samsung" no banco
    When o usuário envia "exclua todas as parcelas do celular"
    Then o agente pergunta sobre o escopo de exclusão
    When o usuário responde "todas"
    Then todas as 6 transações do grupo são removidas do banco
