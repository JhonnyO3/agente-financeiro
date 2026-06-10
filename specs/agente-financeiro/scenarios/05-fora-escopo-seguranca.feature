Feature: Mensagens Fora de Escopo e Segurança
  Como sistema
  Quero tratar corretamente mensagens não financeiras e de números não autorizados
  Para manter a integridade e segurança do agente

  Scenario: Mensagem de saudação recebe resposta amigável com menu
    Given o número autorizado está configurado
    When o usuário envia "oi, tudo bem?"
    Then nenhuma transação é criada no banco
    And a resposta contém saudação
    And a resposta contém menu de opções disponíveis

  Scenario: Agradecimento recebe resposta contextual
    When o usuário envia "obrigado"
    Then a resposta contém resposta contextual curta
    And a resposta contém menu de opções

  Scenario: Número não autorizado não recebe resposta
    Given uma mensagem do número "5511000000000"
    When o número não autorizado envia qualquer mensagem
    Then nenhuma resposta é enviada via Evolution API
    And nenhuma transação é criada no banco
    And o servidor retorna HTTP 200

  Scenario: Número autorizado configurado via variável de ambiente
    Given a variável WHATSAPP_ALLOWED_NUMBER está definida
    Then mensagens do número configurado são processadas
    And mensagens de outros números são descartadas silenciosamente
