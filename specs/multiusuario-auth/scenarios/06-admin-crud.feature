# language: pt
Funcionalidade: CRUD administrativo de usuários e transações (apenas API)

  Como administrador do sistema
  Quero gerenciar usuários e transações de qualquer dono via API protegida
  Para administrar o sistema sem precisar de acesso direto ao banco

  Contexto:
    Dado que as tarefas 03 e 04 foram concluídas
    E existe o usuário Admin (role=ADMIN, email no allowlist, ativo=true) com access_token válido
    E existe o usuário Alice (role=USER) com access_token válido
    E existe o usuário Bob (id=2) com transações cadastradas

  # ---------------------------------------------------------------------------
  # Guard — USER é negado em rotas admin
  # ---------------------------------------------------------------------------

  Cenário: USER é negado em GET /admin/usuarios com 403
    Quando Alice faz GET /admin/usuarios com seu Bearer
    Então a resposta tem status 403
    E o body contém {"erro": "acesso negado"}

  Cenário: USER é negado em POST /admin/usuarios com 403
    Quando Alice faz POST /admin/usuarios com seu Bearer
    Então a resposta tem status 403

  Cenário: Token ADMIN fora do allowlist é negado em todas as rotas admin com 403
    Dado que existe um token forjado com role="ADMIN" e email "fora@allowlist.com"
    E "fora@allowlist.com" não está na ADMIN_EMAILS
    Quando faço GET /admin/usuarios com esse token
    Então a resposta tem status 403
    E o body contém {"erro": "acesso negado"}

  # ---------------------------------------------------------------------------
  # CRUD de usuários — ADMIN
  # ---------------------------------------------------------------------------

  Cenário: ADMIN lista todos os usuários sem senha_hash
    Quando Admin faz GET /admin/usuarios com seu Bearer
    Então a resposta tem status 200
    E o body é uma lista de usuários contendo os campos id, nome, username, email, telefone, role, ativo, criado_em
    E nenhum item da lista contém o campo "senha_hash"

  Cenário: ADMIN obtém usuário por id sem senha_hash
    Dado que existe o usuário id=3
    Quando Admin faz GET /admin/usuarios/3 com seu Bearer
    Então a resposta tem status 200
    E o body contém os campos do usuário sem "senha_hash"

  Cenário: ADMIN tenta obter usuário inexistente e recebe 404
    Quando Admin faz GET /admin/usuarios/9999 com seu Bearer
    Então a resposta tem status 404

  Cenário: ADMIN cria novo usuário com senha bcrypt e recebe 201
    Quando Admin faz POST /admin/usuarios com body {"nome":"Carol","username":"carol","email":"carol@example.com","senha":"abc123","role":"USER"}
    Então a resposta tem status 201
    E o body contém os dados do usuário criado sem o campo "senha_hash"
    E no banco o campo senha_hash é um hash bcrypt (começa com "$2b$")

  Cenário: ADMIN tenta criar usuário com email duplicado e recebe 409
    Dado que existe o usuário com email "carol@example.com"
    Quando Admin faz POST /admin/usuarios com body contendo email "carol@example.com"
    Então a resposta tem status 409

  Cenário: ADMIN edita nome e role de um usuário
    Dado que existe o usuário id=3 com nome "Antigo" e role "USER"
    Quando Admin faz PUT /admin/usuarios/3 com body {"nome":"Novo","role":"ADMIN"}
    Então a resposta tem status 200
    E o body reflete nome "Novo" e role "ADMIN"
    E a resposta não contém "senha_hash"

  Cenário: ADMIN reseta senha de usuário gerando novo hash
    Dado que existe o usuário id=3
    Quando Admin faz PUT /admin/usuarios/3 com body {"senha":"nova-senha-segura"}
    Então a resposta tem status 200
    E no banco o campo senha_hash é atualizado para um novo hash bcrypt
    E o hash antigo não é mais válido para "nova-senha-segura"

  Cenário: ADMIN inativa um usuário
    Dado que existe o usuário id=3 com ativo=true
    Quando Admin faz PUT /admin/usuarios/3 com body {"ativo":false}
    Então a resposta tem status 200
    E no banco o campo ativo é false para o usuário id=3

  Cenário: ADMIN tenta editar usuário inexistente e recebe 404
    Quando Admin faz PUT /admin/usuarios/9999 com body {"nome":"Teste"}
    Então a resposta tem status 404

  Cenário: ADMIN exclui usuário e suas transações são apagadas em cascade
    Dado que o usuário id=2 (Bob) tem 5 transações
    Quando Admin faz DELETE /admin/usuarios/2 com seu Bearer
    Então a resposta tem status 200
    E o usuário id=2 não existe mais no banco
    E as 5 transações de Bob também não existem mais no banco (cascade)

  Cenário: ADMIN tenta excluir usuário inexistente e recebe 404
    Quando Admin faz DELETE /admin/usuarios/9999 com seu Bearer
    Então a resposta tem status 404

  # ---------------------------------------------------------------------------
  # CRUD de transações de qualquer usuário — ADMIN
  # ---------------------------------------------------------------------------

  Cenário: ADMIN lista transações de outro usuário
    Quando Admin faz GET /admin/usuarios/2/transacoes com seu Bearer
    Então a resposta tem status 200
    E o body contém as transações do usuário id=2 (Bob)
    E o shape JSON é idêntico ao shape de /api/transacoes

  Cenário: ADMIN cria transação para outro usuário
    Quando Admin faz POST /admin/usuarios/2/transacoes com body de transação válido
    Então a resposta tem status 201
    E a transação criada tem usuario_id = 2 (Bob)

  Cenário: ADMIN obtém transação de qualquer usuário via GET /admin/transacoes/{id}
    Dado que a transação id=50 pertence ao usuário Bob
    Quando Admin faz GET /admin/transacoes/50 com seu Bearer
    Então a resposta tem status 200
    E o body contém os dados da transação id=50

  Cenário: ADMIN edita transação de qualquer usuário via PUT /admin/transacoes/{id}
    Dado que a transação id=50 pertence ao usuário Bob
    Quando Admin faz PUT /admin/transacoes/50 com dados atualizados
    Então a resposta tem status 200
    E a transação id=50 é atualizada

  Cenário: ADMIN exclui transação de qualquer usuário via DELETE /admin/transacoes/{id}
    Dado que a transação id=50 pertence ao usuário Bob
    Quando Admin faz DELETE /admin/transacoes/50 com seu Bearer
    Então a resposta tem status 200
    E a transação id=50 não existe mais no banco

  Cenário: USER tenta acessar GET /admin/usuarios/{id}/transacoes e recebe 403
    Quando Alice faz GET /admin/usuarios/2/transacoes com seu Bearer
    Então a resposta tem status 403

  Cenário: Excluir usuário não deixa transações órfãs no banco
    Dado que o usuário id=4 tem 3 transações e o usuário id=5 tem 2 transações
    Quando Admin faz DELETE /admin/usuarios/4 com seu Bearer
    Então as 3 transações do usuário id=4 são removidas
    E as 2 transações do usuário id=5 permanecem intactas

  Cenário: Resposta de criação de usuário nunca expõe senha_hash
    Quando Admin cria um novo usuário via POST /admin/usuarios
    Então o body de resposta não contém o campo "senha_hash" em nenhuma profundidade
