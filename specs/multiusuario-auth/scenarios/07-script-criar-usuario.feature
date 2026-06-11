# language: pt
Funcionalidade: Script CLI criar_usuario.py

  Como operador do sistema
  Quero criar usuários via linha de comando com senha bcrypt
  Para inicializar o admin padrão e adicionar novos usuários sem expor senhas

  Contexto:
    Dado que a tarefa 02 (schema) foi concluída
    E o banco de dados está acessível

  # ---------------------------------------------------------------------------
  # Criação bem-sucedida
  # ---------------------------------------------------------------------------

  Cenário: Script cria usuário com role USER por padrão
    Quando executo "uv run python scripts/criar_usuario.py --nome Alice --username alice --email alice@example.com --senha abc123"
    Então o script termina com código de saída 0
    E existe no banco um usuário com email "alice@example.com" e role "USER"
    E a saída informa as credenciais criadas (nome, email, role)

  Cenário: Script cria usuário com role ADMIN quando especificado
    Quando executo o script com --role ADMIN e email "admin@example.com"
    Então o script termina com código de saída 0
    E existe no banco um usuário com email "admin@example.com" e role "ADMIN"

  Cenário: Script cria o usuário admin padrão Jhonatas com role ADMIN
    Quando executo o script com --email "jhonatas2004@gmail.com" --role ADMIN e uma senha fornecida
    Então o script termina com código de saída 0
    E existe no banco um usuário com email "jhonatas2004@gmail.com" e role "ADMIN"

  Cenário: Script aceita telefone opcional
    Quando executo o script com --email "tel@example.com" --telefone "11999990001"
    Então o script termina com código de saída 0
    E o campo telefone do usuário criado é "11999990001"

  # ---------------------------------------------------------------------------
  # Senha bcrypt
  # ---------------------------------------------------------------------------

  Cenário: Senha gravada é hash bcrypt, não texto puro
    Quando executo o script criando o usuário com senha "minha-senha-segura"
    Então o campo senha_hash no banco começa com "$2b$" (formato bcrypt)
    E o valor gravado é diferente de "minha-senha-segura"

  Cenário: Senha não é recuperável — hash é one-way
    Dado que o usuário foi criado com senha "segredo-123"
    Quando consulto diretamente o campo senha_hash no banco
    Então não é possível derivar "segredo-123" a partir do hash

  Cenário: Login funciona com a senha fornecida ao script
    Dado que o script criou o usuário com email "alice@example.com" e senha "abc123"
    Quando envio POST /auth/login com body {"email":"alice@example.com","senha":"abc123"}
    Então a resposta tem status 200 e retorna access_token

  # ---------------------------------------------------------------------------
  # Email duplicado — idempotência
  # ---------------------------------------------------------------------------

  Cenário: Executar o script com email já existente atualiza o hash e exibe mensagem clara
    Dado que existe o usuário com email "alice@example.com"
    Quando executo o script novamente com --email "alice@example.com" e --senha "nova-senha"
    Então o script termina com código de saída 0
    E a saída exibe mensagem indicando que o usuário já existia e foi atualizado
    E o campo senha_hash do usuário foi atualizado para o hash de "nova-senha"

  Cenário: Após idempotência, login funciona com a nova senha
    Dado que o script atualizou a senha de "alice@example.com" para "nova-senha"
    Quando envio POST /auth/login com body {"email":"alice@example.com","senha":"nova-senha"}
    Então a resposta tem status 200

  Cenário: Após idempotência, login com senha antiga falha
    Dado que o script atualizou a senha de "alice@example.com" de "abc123" para "nova-senha"
    Quando envio POST /auth/login com body {"email":"alice@example.com","senha":"abc123"}
    Então a resposta tem status 401

  # ---------------------------------------------------------------------------
  # Erros de entrada
  # ---------------------------------------------------------------------------

  Cenário: Script falha com mensagem clara quando parâmetro obrigatório está ausente
    Quando executo o script sem o argumento --email
    Então o script termina com código de saída diferente de 0
    E a saída de erro indica o parâmetro faltante

  Cenário: Script não expõe a senha em texto puro na saída
    Quando executo o script com --senha "segredo-especial"
    Então a saída do script não contém "segredo-especial"
