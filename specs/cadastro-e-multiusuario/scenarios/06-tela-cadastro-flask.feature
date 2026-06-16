# language: pt
Funcionalidade: Tela de cadastro de usuário (dashboard Flask)
  RN-01, RN-02, RN-05, RN-07. Reusa POST /admin/usuarios.

  Cenário: Admin acessa o formulário de cadastro
    Dado um admin autenticado
    Quando acesso GET "/admin/usuarios/novo"
    Então recebo status 200 com o formulário

  Cenário: Não-admin é redirecionado para login
    Dado um usuário autenticado com role USER
    Quando acesso GET "/admin/usuarios/novo"
    Então sou redirecionado para a tela de login

  Cenário: Cadastro com sucesso
    Dado um admin autenticado
    E o backend responde 201 ao POST /admin/usuarios
    Quando submeto nome "João Silva", email "joao@exemplo.com", telefone "5511999998888" e senha "segredo123"
    Então o backend é chamado com username "joao" e telefone "5511999998888"
    E vejo a mensagem de sucesso e sou redirecionado

  Cenário: E-mail duplicado preserva os campos
    Dado um admin autenticado
    E o backend responde 409 ao POST /admin/usuarios
    Quando submeto um cadastro com email já existente
    Então vejo "Este e-mail já está cadastrado."
    E o nome e o telefone preenchidos são mantidos
    E a senha não é reexibida

  Cenário: Telefone não numérico é rejeitado sem chamar o backend
    Dado um admin autenticado
    Quando submeto telefone "(11) abc"
    Então vejo erro de validação
    E o backend não é chamado

  Cenário: E-mail sem arroba é rejeitado sem chamar o backend
    Dado um admin autenticado
    Quando submeto email "joaoexemplo.com"
    Então vejo erro de validação
    E o backend não é chamado
