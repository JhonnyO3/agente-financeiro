# language: pt

Funcionalidade: EvolutionApiClient robusto com raise_for_status e retry
  Como worker
  Quero que o cliente de envio de mensagens falhe explicitamente em erros HTTP
  E tente novamente em falhas transitórias sem mascarar o erro

  Cenário: envio bem-sucedido HTTP 200 nao levanta excecao
    Dado um cliente HTTP mockado que retorna HTTP 200
    Quando chamo evolution_client.enviar_mensagem("5511999999999", "ola")
    Então nenhuma exceção é levantada

  Cenário: resposta HTTP 4xx levanta excecao imediatamente
    Dado um cliente HTTP mockado que retorna HTTP 400
    Quando chamo evolution_client.enviar_mensagem("5511999999999", "ola")
    Então uma exceção é levantada (equivalente a raise_for_status)
    E nenhum retry e feito (erro de cliente nao e retentavel)

  Cenário: resposta HTTP 500 tenta novamente com backoff e propaga excecao apos esgotar
    Dado um cliente HTTP mockado que sempre retorna HTTP 500
    E um spy no asyncio.sleep (substituto de tenacity)
    Quando chamo evolution_client.enviar_mensagem("5511999999999", "ola")
    Então asyncio.sleep foi chamado pelo menos 1 vez (backoff)
    E apos esgotar as tentativas uma exceção é levantada

  Cenário: resposta HTTP 503 e retentavel e sucesso na segunda tentativa nao levanta excecao
    Dado um cliente HTTP mockado que retorna HTTP 503 na primeira chamada e HTTP 200 na segunda
    Quando chamo evolution_client.enviar_mensagem("5511999999999", "ola")
    Então nenhuma exceção é levantada
    E o envio foi realizado na segunda tentativa

  Cenário: timeout explícito e respeitado
    Dado um cliente HTTP mockado configurado para timeout
    Quando chamo evolution_client.enviar_mensagem com timeout ultrapassado
    Então uma exceção de timeout é levantada
    E a mensagem nao foi enviada silenciosamente
