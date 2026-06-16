# language: pt
Funcionalidade: Buscar usuário por telefone no repositório
  RN-03, RN-07, RN-11. UsuarioRepository.buscar_por_telefone filtra por ativo e normaliza.

  Cenário: Usuário ativo é encontrado pelo telefone
    Dado um usuário ativo com telefone "5511999998888"
    Quando busco por telefone "5511999998888"
    Então recebo o usuário correspondente

  Cenário: Usuário inativo não é encontrado
    Dado um usuário com telefone "5511999998888" e ativo igual a False
    Quando busco por telefone "5511999998888"
    Então recebo None

  Cenário: Telefone inexistente retorna None
    Dado que nenhum usuário tem o telefone "5511000000000"
    Quando busco por telefone "5511000000000"
    Então recebo None

  Cenário: Telefone com máscara é normalizado antes da busca
    Dado um usuário ativo com telefone "5511999998888"
    Quando busco por telefone "+55 (11) 99999-8888"
    Então recebo o usuário correspondente

  Cenário: Telefone vazio não consulta o banco
    Quando busco por telefone "   "
    Então recebo None sem executar consulta filtrada
