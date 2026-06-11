# language: pt
Funcionalidade: Autenticação backend — JWT, guard, hashing

  Como backend FastAPI
  Quero emitir e validar access+refresh tokens JWT HS256
  Para autenticar usuários e proteger todos os endpoints de dados

  Contexto:
    Dado que a tarefa 02 (schema) foi concluída
    E JWT_SECRET está configurado no ambiente
    E existe o usuário ativo com email "alice@example.com" e senha "senha-correta"
    E existe o usuário inativo com email "inativo@example.com" e senha "qualquer"

  # ---------------------------------------------------------------------------
  # POST /auth/login
  # ---------------------------------------------------------------------------

  Cenário: Login com credenciais válidas retorna access e refresh token
    Quando envio POST /auth/login com body {"email": "alice@example.com", "senha": "senha-correta"}
    Então a resposta tem status 200
    E o body contém "access_token", "refresh_token", "token_type": "bearer" e "role"
    E o access_token decodificado contém "sub", "role", "email", "type": "access" e "exp"
    E o refresh_token decodificado contém "sub", "type": "refresh", "jti" e "exp"

  Cenário: Login com senha errada retorna 401 genérico
    Quando envio POST /auth/login com body {"email": "alice@example.com", "senha": "errada"}
    Então a resposta tem status 401
    E o body contém {"erro": "credenciais inválidas"}
    E o body não indica qual campo falhou (email ou senha)

  Cenário: Login com email inexistente retorna 401 genérico
    Quando envio POST /auth/login com body {"email": "nao@existe.com", "senha": "qualquer"}
    Então a resposta tem status 401
    E o body contém {"erro": "credenciais inválidas"}

  Cenário: Login com usuário inativo retorna 401 genérico
    Quando envio POST /auth/login com body {"email": "inativo@example.com", "senha": "qualquer"}
    Então a resposta tem status 401
    E o body contém {"erro": "credenciais inválidas"}

  # ---------------------------------------------------------------------------
  # POST /auth/refresh
  # ---------------------------------------------------------------------------

  Cenário: Refresh com token válido retorna novo access e novo refresh
    Dado que Alice possui um refresh_token válido e ativo
    Quando envio POST /auth/refresh com body {"refresh_token": "<refresh de Alice>"}
    Então a resposta tem status 200
    E o body contém "access_token", "refresh_token" e "token_type": "bearer"
    E o novo refresh_token possui um jti diferente do anterior

  Cenário: Refresh rota o refresh token (jti anterior fica inválido)
    Dado que Alice realizou um refresh e obteve novo refresh_token
    Quando envio POST /auth/refresh com o refresh_token ANTERIOR (jti revogado)
    Então a resposta tem status 401
    E o body contém {"erro": "refresh inválido"}

  Cenário: Refresh com token expirado retorna 401
    Dado que existe um refresh_token cujo exp está no passado
    Quando envio POST /auth/refresh com esse token
    Então a resposta tem status 401
    E o body contém {"erro": "refresh inválido"}

  Cenário: Refresh com assinatura inválida retorna 401
    Quando envio POST /auth/refresh com um token assinado com segredo diferente
    Então a resposta tem status 401
    E o body contém {"erro": "refresh inválido"}

  Cenário: Refresh com access_token (type incorreto) retorna 401
    Dado que Alice possui um access_token válido
    Quando envio POST /auth/refresh passando o access_token no lugar do refresh_token
    Então a resposta tem status 401
    E o body contém {"erro": "refresh inválido"}

  # ---------------------------------------------------------------------------
  # POST /auth/logout
  # ---------------------------------------------------------------------------

  Cenário: Logout revoga o refresh token corrente
    Dado que Alice possui um refresh_token válido e ativo
    Quando envio POST /auth/logout com body {"refresh_token": "<refresh de Alice>"}
    Então a resposta tem status 200
    E o body contém {"ok": true}
    E ao tentar usar esse refresh_token em POST /auth/refresh a resposta é 401

  Cenário: Logout é idempotente para token já revogado
    Dado que Alice já revogou seu refresh_token via logout
    Quando envio POST /auth/logout novamente com o mesmo refresh_token
    Então a resposta tem status 200
    E o body contém {"ok": true}

  # ---------------------------------------------------------------------------
  # Guard get_usuario_atual
  # ---------------------------------------------------------------------------

  Cenário: Endpoint protegido sem header Authorization retorna 401
    Quando faço GET /api/transacoes sem nenhum header Authorization
    Então a resposta tem status 401
    E o body contém {"erro": "não autenticado"}

  Cenário: Endpoint protegido com Bearer malformado retorna 401
    Quando faço GET /api/transacoes com Authorization: Bearer token-invalido-nao-jwt
    Então a resposta tem status 401
    E o body contém {"erro": "não autenticado"}

  Cenário: Endpoint protegido com access_token expirado retorna 401
    Dado que Alice possui um access_token cujo exp está no passado
    Quando faço GET /api/transacoes com Authorization: Bearer <access expirado>
    Então a resposta tem status 401
    E o body contém {"erro": "não autenticado"}

  Cenário: Endpoint protegido com access_token válido é aceito e injeta usuario_id
    Dado que Alice possui um access_token válido
    Quando faço GET /api/transacoes com Authorization: Bearer <access de Alice>
    Então a resposta tem status 200
    E apenas as transações de Alice são retornadas

  Cenário: Usar refresh_token (type=refresh) onde se espera access_token retorna 401
    Dado que Alice possui um refresh_token válido
    Quando faço GET /api/transacoes com Authorization: Bearer <refresh de Alice>
    Então a resposta tem status 401
    E o body contém {"erro": "não autenticado"}

  # ---------------------------------------------------------------------------
  # Guard get_admin
  # ---------------------------------------------------------------------------

  Cenário: get_admin aceita token de ADMIN com email no allowlist e usuário ativo no banco
    Dado que existe o usuário "admin@exemplo.com" com role ADMIN, ativo=true
    E "admin@exemplo.com" está na ADMIN_EMAILS do .env
    E o token de acesso desse usuário é válido e contém role="ADMIN"
    Quando faço GET /admin/usuarios com o Bearer desse token
    Então a resposta tem status 200

  Cenário: get_admin rejeita token com role=USER com 403
    Dado que Alice possui role USER e um access_token válido
    Quando faço GET /admin/usuarios com o Bearer de Alice
    Então a resposta tem status 403
    E o body contém {"erro": "acesso negado"}

  Cenário: get_admin rejeita token forjado com role=ADMIN cujo email não está no allowlist
    Dado que um token forjado válido contém role="ADMIN" e email "invasor@exemplo.com"
    E "invasor@exemplo.com" NÃO está na ADMIN_EMAILS
    Quando faço GET /admin/usuarios com esse Bearer forjado
    Então a resposta tem status 403
    E o body contém {"erro": "acesso negado"}

  Cenário: get_admin rejeita ADMIN que está no allowlist mas foi desativado no banco
    Dado que o usuário "admin@exemplo.com" está na ADMIN_EMAILS
    E no banco o registro desse usuário tem ativo=false
    E o access_token ainda é válido (não expirou)
    Quando faço GET /admin/usuarios com o Bearer desse token
    Então a resposta tem status 403
    E o body contém {"erro": "acesso negado"}

  Cenário: get_admin rejeita ADMIN com role rebaixada para USER no banco após emissão do token
    Dado que o token de "admin@exemplo.com" foi emitido com role="ADMIN"
    E após a emissão o banco foi atualizado para role="USER" para esse usuário
    Quando faço GET /admin/usuarios com o Bearer desse token
    Então a resposta tem status 403
    E o body contém {"erro": "acesso negado"}

  # ---------------------------------------------------------------------------
  # Hashing
  # ---------------------------------------------------------------------------

  Cenário: hash_senha gera hash bcrypt diferente do texto original
    Quando chamo hash_senha("minha-senha")
    Então o resultado é uma string que começa com "$2b$" (formato bcrypt)
    E o resultado é diferente de "minha-senha"

  Cenário: verificar_senha retorna True para senha e hash corretos
    Dado que hash = hash_senha("minha-senha")
    Quando chamo verificar_senha("minha-senha", hash)
    Então retorna True

  Cenário: verificar_senha retorna False para senha incorreta
    Dado que hash = hash_senha("minha-senha")
    Quando chamo verificar_senha("outra-senha", hash)
    Então retorna False

  # ---------------------------------------------------------------------------
  # Config / boot
  # ---------------------------------------------------------------------------

  Cenário: Backend não sobe quando JWT_SECRET está ausente
    Dado que JWT_SECRET não está definido no ambiente
    Quando tento iniciar o backend FastAPI
    Então a inicialização falha com erro explícito de configuração
    E a aplicação não fica em estado de escuta
