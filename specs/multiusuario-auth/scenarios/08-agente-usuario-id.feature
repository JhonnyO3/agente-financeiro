# language: pt
Funcionalidade: Agente WhatsApp grava usuario_id do usuário padrão

  Como agente WhatsApp single-user
  Quero resolver o usuario_id do usuário padrão no startup
  Para que todas as transações criadas via WhatsApp fiquem vinculadas ao dono correto

  Contexto:
    Dado que a tarefa 03 (repository) foi concluída
    E existe o usuário Jhonatas com email "jhonatas2004@gmail.com" e id=1 no banco
    E a variável AGENTE_USUARIO_EMAIL é "jhonatas2004@gmail.com"

  # ---------------------------------------------------------------------------
  # Resolução do usuario_id no lifespan
  # ---------------------------------------------------------------------------

  Cenário: Lifespan do agente resolve o usuario_id do usuário padrão por email
    Quando o agente é iniciado
    Então o lifespan consulta UsuarioRepository.buscar_por_email("jhonatas2004@gmail.com")
    E o usuario_id resolvido é 1
    E esse id é injetado no CadastrarService

  Cenário: Lifespan falha de forma explícita se AGENTE_USUARIO_EMAIL não encontrar usuário no banco
    Dado que o banco não contém nenhum usuário com email "jhonatas2004@gmail.com"
    Quando o agente é iniciado
    Então a inicialização falha com mensagem explicando que o usuário padrão não foi encontrado

  # ---------------------------------------------------------------------------
  # Transação criada com usuario_id correto
  # ---------------------------------------------------------------------------

  Cenário: Agente cadastra gasto simples com usuario_id do usuário padrão
    Dado que o agente está em execução com usuario_id=1 resolvido
    Quando o usuário autorizado envia a mensagem "Gastei 50 reais no mercado"
    Então o agente cria uma transação no banco com usuario_id = 1
    E o campo responsavel permanece como valor livre (não é sobrescrito pelo usuario_id)

  Cenário: Agente cadastra receita com usuario_id do usuário padrão
    Dado que o agente está em execução com usuario_id=1 resolvido
    Quando o usuário autorizado envia a mensagem "Recebi 3000 de salário"
    Então a transação criada no banco tem usuario_id = 1

  Cenário: Agente cadastra transação parcelada e todas as parcelas têm usuario_id correto
    Dado que o agente está em execução com usuario_id=1 resolvido
    Quando o usuário autorizado envia uma transação parcelada em 3 vezes
    Então as 3 transações criadas no banco têm usuario_id = 1
    E todas compartilham o mesmo grupo_parcela_id

  Cenário: Agente cria lote de transações e todos os registros têm usuario_id correto
    Dado que o agente está em execução com usuario_id=1 resolvido
    Quando o usuário autorizado envia múltiplas transações de uma vez
    Então todas as transações do lote são gravadas com usuario_id = 1

  # ---------------------------------------------------------------------------
  # Consultas seguem funcionando
  # ---------------------------------------------------------------------------

  Cenário: Consulta de saldo pelo agente funciona para o usuário padrão após migração
    Dado que existem transações do usuário Jhonatas (usuario_id=1)
    Quando o usuário autorizado envia "Qual meu saldo?"
    Então o agente retorna o saldo calculado apenas das transações com usuario_id = 1

  Cenário: Consulta de parcelas ativas pelo agente funciona para o usuário padrão
    Dado que existem parcelas ativas do usuário Jhonatas (usuario_id=1)
    Quando o usuário autorizado solicita as parcelas ativas
    Então o agente retorna apenas as parcelas do usuário Jhonatas

  # ---------------------------------------------------------------------------
  # Comportamento single-user inalterado
  # ---------------------------------------------------------------------------

  Cenário: Mensagem de número não autorizado é ignorada silenciosamente
    Dado que WHATSAPP_ALLOWED_NUMBER é "+5511999990001"
    Quando chega uma mensagem do número "+5511888880001"
    Então o webhook retorna 200 sem criar nenhuma transação
    E nenhuma transação é gravada com qualquer usuario_id

  Cenário: usuario_id do agente não muda em tempo de execução (single-user)
    Dado que o agente foi iniciado com usuario_id=1
    Quando processam múltiplas mensagens ao longo do tempo
    Então todas as transações criadas continuam com usuario_id = 1
