# language: pt
Funcionalidade: Configuração final, start.py e .env.example

  Como desenvolvedor ou operador do sistema
  Quero que todas as variáveis de ambiente estejam documentadas e que o boot falhe claramente sem elas
  Para garantir que nenhuma instalação suba com configuração incompleta

  Contexto:
    Dado que as tarefas 05, 06, 07, 08 e 09 foram concluídas

  # ---------------------------------------------------------------------------
  # .env.example — documentação das variáveis
  # ---------------------------------------------------------------------------

  Cenário: .env.example documenta JWT_SECRET
    Quando leio o arquivo .env.example
    Então existe a entrada "JWT_SECRET" sem valor real (ex.: placeholder ou comentário)

  Cenário: .env.example documenta JWT_ACCESS_EXPIRES_MIN
    Quando leio o arquivo .env.example
    Então existe a entrada "JWT_ACCESS_EXPIRES_MIN" com exemplo numérico (ex.: 30)

  Cenário: .env.example documenta JWT_REFRESH_EXPIRES_DAYS
    Quando leio o arquivo .env.example
    Então existe a entrada "JWT_REFRESH_EXPIRES_DAYS" com exemplo numérico (ex.: 7)

  Cenário: .env.example documenta ADMIN_EMAILS
    Quando leio o arquivo .env.example
    Então existe a entrada "ADMIN_EMAILS" com formato CSV de exemplo

  Cenário: .env.example documenta SECRET_KEY
    Quando leio o arquivo .env.example
    Então existe a entrada "SECRET_KEY" sem valor real

  Cenário: .env.example documenta AGENTE_USUARIO_EMAIL
    Quando leio o arquivo .env.example
    Então existe a entrada "AGENTE_USUARIO_EMAIL" com o default "jhonatas2004@gmail.com" como exemplo

  Cenário: .env.example não contém valores reais de segredos
    Quando leio o arquivo .env.example
    Então nenhum valor de JWT_SECRET ou SECRET_KEY é uma string secreta real (todos são placeholders)

  # ---------------------------------------------------------------------------
  # Boot sem variáveis obrigatórias — falha explícita
  # ---------------------------------------------------------------------------

  Cenário: Backend não sobe sem JWT_SECRET definido
    Dado que JWT_SECRET não está definido no ambiente
    Quando tento iniciar o backend FastAPI
    Então a inicialização falha com erro de configuração explícito
    E a mensagem de erro menciona "JWT_SECRET"

  Cenário: Frontend não sobe sem SECRET_KEY definido
    Dado que SECRET_KEY não está definido no ambiente
    Quando tento iniciar o frontend Flask
    Então a inicialização falha com erro de configuração explícito
    E a mensagem de erro menciona "SECRET_KEY"

  Cenário: Agente não sobe se AGENTE_USUARIO_EMAIL não encontrar usuário no banco
    Dado que AGENTE_USUARIO_EMAIL aponta para um email sem usuário cadastrado
    Quando tento iniciar o agente
    Então a inicialização falha com mensagem explicando que o usuário padrão não existe

  # ---------------------------------------------------------------------------
  # start.py — subida dos três processos
  # ---------------------------------------------------------------------------

  Cenário: start.py sobe o agente com a referência agent.entrypoint.main:app
    Quando leio a variável AGENTE_CMD em start.py
    Então o valor é "agent.entrypoint.main:app"
    E não há referência a "app.entrypoint.main:app"

  Cenário: uv run python start.py sobe agente, backend e frontend
    Dado que todas as variáveis de ambiente obrigatórias estão configuradas corretamente
    E o banco de dados está acessível com o usuário padrão cadastrado
    Quando executo "uv run python start.py"
    Então o agente é iniciado na porta configurada para o agente
    E o backend FastAPI é iniciado na porta 8000
    E o frontend Flask é iniciado na porta 5000
    E nenhum dos três processos termina imediatamente com erro

  Cenário: start.py lê as novas configurações de auth sem erro
    Dado que JWT_SECRET, ADMIN_EMAILS, SECRET_KEY e AGENTE_USUARIO_EMAIL estão definidos
    Quando executo "uv run python start.py"
    Então nenhum dos processos lança ValidationError ou erro de settings na inicialização

  # ---------------------------------------------------------------------------
  # Integração completa pós-feature (smoke test E2E)
  # ---------------------------------------------------------------------------

  Cenário: Suite de testes completa passa após todas as tarefas integradas
    Quando executo "uv run pytest -q"
    Então todos os testes passam sem falhas
    E nenhum teste importa o namespace "app."

  Cenário: alembic upgrade head aplica todas as migrations sem erro
    Dado que o banco está com schema anterior à feature
    Quando executo "uv run alembic upgrade head"
    Então todas as migrations são aplicadas com sucesso
    E a tabela usuarios existe com todos os campos definidos no contrato
    E a coluna usuario_id em transacoes é NOT NULL

  Cenário: Dois usuários distintos não veem dados um do outro após integração total
    Dado que Alice e Bob estão cadastrados e possuem transações distintas
    Quando Alice faz login e acessa GET /api/transacoes
    Então vê apenas as próprias transações
    Quando Bob faz login e acessa GET /api/transacoes
    Então vê apenas as próprias transações
    E nenhum dos dois vê transações do outro
