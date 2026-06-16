# language: pt
Funcionalidade: Webhook resolve identidade por telefone (in-process)
  RN-10, RN-11, RN-15, RN-16. Sem WHATSAPP_ALLOWED_NUMBER.

  Contexto:
    Dado um webhook com apikey válida e payload de mensagem de texto

  Cenário: Número não cadastrado é descartado silenciosamente
    Dado que a resolução por telefone retorna None
    Quando o webhook recebe a mensagem
    Então responde 200
    E nada é enfileirado

  Cenário: Usuário inativo é descartado silenciosamente
    Dado que a resolução por telefone retorna None (usuário inativo)
    Quando o webhook recebe a mensagem
    Então responde 200
    E nada é enfileirado

  Cenário: Usuário ativo é enfileirado com seu usuario_id
    Dado que a resolução por telefone retorna o usuário de id 42
    Quando o webhook recebe a mensagem do número "5511999998888" com texto "gastei 50"
    Então a fila recebe a tupla (42, "5511999998888", "gastei 50")
    E responde 200

  Cenário: apikey inválida é rejeitada
    Dado um webhook com apikey inválida
    Quando o webhook recebe a mensagem
    Então responde 401
    E nada é enfileirado

  Cenário: Mensagem própria (fromMe) é ignorada
    Dado um payload com fromMe verdadeiro
    Quando o webhook recebe a mensagem
    Então responde 200
    E nada é enfileirado

  Cenário: Não há mais referência a WHATSAPP_ALLOWED_NUMBER
    Então o webhook não lê WHATSAPP_ALLOWED_NUMBER
