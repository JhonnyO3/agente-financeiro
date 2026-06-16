# language: pt
Funcionalidade: Resolução de identidade por telefone via /auth
  Endpoint GET /auth/identidade/por-telefone/{telefone}, isolado das regras de admin.

  Contexto:
    Dado um cliente autenticado com token válido

  Cenário: Telefone de usuário ativo retorna 200 com dados
    Dado um usuário ativo com telefone "5511999998888"
    Quando faço GET em "/auth/identidade/por-telefone/5511999998888"
    Então recebo status 200
    E o corpo contém id, nome, email, telefone e ativo

  Cenário: Telefone de usuário inativo retorna 204
    Dado um usuário inativo com telefone "5511999998888"
    Quando faço GET em "/auth/identidade/por-telefone/5511999998888"
    Então recebo status 204 sem corpo

  Cenário: Telefone inexistente retorna 204
    Quando faço GET em "/auth/identidade/por-telefone/5511000000000"
    Então recebo status 204 sem corpo

  Cenário: Inativo e inexistente são indistinguíveis
    Então a resposta para inativo e para inexistente é a mesma (204 sem corpo)

  Cenário: Sem autenticação retorna 401
    Dado um cliente sem token
    Quando faço GET em "/auth/identidade/por-telefone/5511999998888"
    Então recebo status 401
