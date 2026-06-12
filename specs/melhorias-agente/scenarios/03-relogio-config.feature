# language: pt

Funcionalidade: Relogio injetavel com fuso horario e Settings com campos obrigatorios
  Como tools e entrypoint
  Quero um relógio cujo fuso é configurável e injetável
  Para que datas sejam corretas no horário do usuário e testáveis com relógio fixo

  Cenário: hoje() retorna a data no fuso America/Sao_Paulo quando UTC ja virou o dia
    Dado um relógio fixo com datetime UTC = "2026-06-12T03:00:00Z" (BRT ainda é 11/06)
    Quando chamo Relogio("America/Sao_Paulo").hoje() usando esse relógio fixo
    Então retorna date(2026, 6, 11)
    E não retorna date(2026, 6, 12)

  Cenário: agora() retorna datetime aware no fuso configurado
    Dado um relógio criado com tz "America/Sao_Paulo"
    Quando chamo agora()
    Então o datetime retornado é aware (tzinfo não é None)
    E o fuso é America/Sao_Paulo

  Cenário: Relogio aceita fuso alternativo
    Dado um relógio criado com tz "UTC"
    Quando chamo hoje()
    Então a data é coerente com UTC

  Cenário: Settings falha explicitamente sem RESPONSAVEL_PADRAO
    Dado variáveis de ambiente sem RESPONSAVEL_PADRAO definido
    Quando tento instanciar Settings
    Então uma exceção de validação é levantada mencionando RESPONSAVEL_PADRAO

  Cenário: Settings falha explicitamente sem WEBHOOK_APIKEY
    Dado variáveis de ambiente sem WEBHOOK_APIKEY definido
    Quando tento instanciar Settings
    Então uma exceção de validação é levantada mencionando WEBHOOK_APIKEY

  Cenário: Settings falha explicitamente sem AGENTE_USUARIO_EMAIL
    Dado variáveis de ambiente sem AGENTE_USUARIO_EMAIL definido
    Quando tento instanciar Settings
    Então uma exceção de validação é levantada mencionando AGENTE_USUARIO_EMAIL

  Cenário: Settings carrega valores padrao para campos opcionais
    Dado variáveis de ambiente com RESPONSAVEL_PADRAO, WEBHOOK_APIKEY e AGENTE_USUARIO_EMAIL definidos
    Quando instancio Settings
    Então TIMEZONE_USUARIO é "America/Sao_Paulo"
    E DEBOUNCE_SEGUNDOS é 5
    E CONFIANCA_MINIMA é 0.7
    E RAG_PISO é 1.0
    E RAG_MARGEM é 0.15
