# language: pt

Funcionalidade: Webhook com auth e dedup, Worker com debounce e tratamento de erro
  Como Evolution API
  Quero que o webhook autentique por apikey, filtre eventos indevidos e deduplique mensagens
  E que o worker agrupe fragmentos e nunca silencie erros

  # ---- AUTENTICACAO ----

  Cenário: apikey correta retorna 200
    Dado Settings.WEBHOOK_APIKEY = "minha-chave"
    E uma requisicao POST /webhook/mensagem com header apikey="minha-chave" e payload valido
    Quando o webhook processa a requisicao
    Então retorna HTTP 200

  Cenário: apikey ausente retorna 401
    Dado uma requisicao POST /webhook/mensagem sem header apikey
    Quando o webhook processa a requisicao
    Então retorna HTTP 401
    E a fila nao recebeu nenhum item

  Cenário: apikey incorreta retorna 401
    Dado Settings.WEBHOOK_APIKEY = "minha-chave"
    E uma requisicao com header apikey="chave-errada"
    Quando o webhook processa a requisicao
    Então retorna HTTP 401

  # ---- FILTROS SILENCIOSOS (retornam 200 sem processar) ----

  Esquema do Cenário: filtros silenciosos retornam 200 sem enfileirar
    Dado uma requisicao autenticada com campo "<campo>" = "<valor>"
    Quando o webhook processa a requisicao
    Então retorna HTTP 200
    E a fila nao recebeu nenhum item

    Exemplos:
      | campo        | valor                    |
      | evento       | messages.update          |
      | fromMe       | true                     |
      | numero       | 5511999999999 (diferente do ALLOWED) |
      | texto        | (ausente/vazio)          |

  # ---- DEDUP ----

  Cenário: message_id duplicado e processado apenas uma vez
    Dado uma requisicao autenticada valida com message_id="MSG001"
    Quando o webhook processa a mesma requisicao duas vezes com message_id="MSG001"
    Então a fila recebe exatamente 1 item (nao 2)

  Cenário: dois message_ids distintos sao ambos enfileirados
    Dado duas requisicoes autenticadas validas com message_id="MSG001" e message_id="MSG002"
    Quando o webhook processa as duas requisicoes
    Então a fila recebe 2 itens

  # ---- DEBOUNCE ----

  Cenário: dois fragmentos em menos de 5 segundos sao agrupados com \n
    Dado um worker com debounce de 5 segundos mockado
    E dois textos "gastei" e "30 no uber" chegando em menos de 5s para o mesmo numero
    Quando o debounce dispara
    Então o Classificador recebe o texto "gastei\n30 no uber" (um unico processamento)

  Cenário: mensagem unica sem fragmentos e processada normalmente
    Dado um texto "listar gastos" chegando sozinho
    Quando o debounce dispara
    Então o Classificador recebe o texto "listar gastos" sem alteracao

  # ---- HISTORICO ----

  Cenário: worker registra mensagem do usuario e resposta no estado apos processar
    Dado um Classificador mockado e Roteador mockado e EvolutionClient mockado
    E EstadoStore mockado
    Quando o worker processa a mensagem "listar gastos" e obtém resposta
    Então EstadoStore.registrar_mensagem foi chamado com papel="usuario" e o texto agrupado
    E EstadoStore.registrar_mensagem foi chamado com papel="assistente" e a resposta

  # ---- TRATAMENTO DE ERRO ----

  Cenário: excecao no processamento envia mensagem de falha amigavel ao usuario
    Dado um Classificador mockado que lanca RuntimeError("falha inesperada")
    E um EvolutionClient mockado
    Quando o worker tenta processar a mensagem do usuario
    Então EvolutionClient.enviar_mensagem foi chamado com uma mensagem de erro amigavel
    E nenhuma excecao propagou silenciosamente para fora do worker

  Cenário: webhook nao loga payload completo em INFO (protecao de PII)
    Dado um logger mockado em nivel INFO
    E uma requisicao com payload contendo numero e texto do usuario
    Quando o webhook processa a requisicao
    Então o logger INFO nao foi chamado com o payload completo
