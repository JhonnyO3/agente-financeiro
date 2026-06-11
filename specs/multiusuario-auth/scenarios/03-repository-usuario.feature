# language: pt
Funcionalidade: Repository com filtro por usuario_id e UsuarioRepository

  Como serviço do backend
  Quero que o TransacaoRepository filtre por usuario_id e que exista um UsuarioRepository
  Para que transações sejam isoladas por dono e usuários sejam gerenciados corretamente

  Contexto:
    Dado que a tarefa 02 (schema) foi concluída
    E o banco contém a tabela usuarios e a coluna usuario_id em transacoes

  # ---------------------------------------------------------------------------
  # TransacaoRepository — filtro por usuario_id
  # ---------------------------------------------------------------------------

  Cenário: Listar transações filtra por usuario_id quando informado
    Dado que existem 3 transações do usuário 1 e 2 transações do usuário 2
    Quando chamo transacao_repository.listar_por_periodo(usuario_id=1, ...)
    Então retorno contém apenas as 3 transações do usuário 1
    E nenhuma transação do usuário 2 aparece no resultado

  Cenário: Listar transações com usuario_id=None retorna todas
    Dado que existem transações de múltiplos usuários
    Quando chamo transacao_repository.listar_por_periodo(usuario_id=None, ...)
    Então retorno contém transações de todos os usuários (sem filtro)

  Cenário: Criar transação com usuario_id preenchido persiste o vínculo
    Dado que existe o usuário com id 1
    Quando chamo transacao_repository.criar(TransacaoCreate(usuario_id=1, ...))
    Então a transação é salva no banco com usuario_id = 1

  Cenário: TransacaoCreate sem usuario_id falha na criação
    Quando tento instanciar TransacaoCreate sem fornecer usuario_id
    Então a instanciação falha com ValidationError (campo obrigatório)

  Cenário: TransacaoUpdate não possui campo usuario_id
    Quando instancio TransacaoUpdate com os dados permitidos
    Então o objeto não possui atributo usuario_id
    E tentar passar usuario_id no construtor é ignorado ou falha conforme o DTO

  Cenário: buscar_por_id com usuario_id correto retorna a transacao
    Dado que existe a transação id=10 pertencente ao usuário 1
    Quando chamo transacao_repository.buscar_por_id(id=10, usuario_id=1)
    Então retorna a transação com id=10

  Cenário: buscar_por_id com usuario_id de outro dono retorna None
    Dado que existe a transação id=10 pertencente ao usuário 1
    Quando chamo transacao_repository.buscar_por_id(id=10, usuario_id=2)
    Então retorna None

  Cenário: excluir transação com usuario_id de outro dono não exclui nada
    Dado que existe a transação id=10 pertencente ao usuário 1
    Quando chamo transacao_repository.excluir(id=10, usuario_id=2)
    Então a transação id=10 ainda existe no banco

  Cenário: excluir_grupo com usuario_id correto remove apenas o grupo do dono
    Dado que o grupo "grupo-abc" tem 3 parcelas do usuário 1
    Quando chamo transacao_repository.excluir_grupo(grupo="grupo-abc", usuario_id=1)
    Então as 3 parcelas do grupo "grupo-abc" são removidas

  Cenário: excluir_grupo com usuario_id de outro dono não remove nada
    Dado que o grupo "grupo-abc" tem 3 parcelas do usuário 1
    Quando chamo transacao_repository.excluir_grupo(grupo="grupo-abc", usuario_id=2)
    Então as 3 parcelas do grupo "grupo-abc" permanecem no banco

  Cenário: agregar_por_categoria filtra por usuario_id
    Dado que existem gastos de "Alimentação" do usuário 1 e gastos de "Alimentação" do usuário 2
    Quando chamo transacao_repository.agregar_por_categoria(usuario_id=1, ...)
    Então o resultado inclui apenas os gastos de "Alimentação" do usuário 1

  # ---------------------------------------------------------------------------
  # UsuarioRepository
  # ---------------------------------------------------------------------------

  Cenário: criar usuário e recuperar por id
    Dado que nenhum usuário existe com email "bob@example.com"
    Quando chamo usuario_repository.criar(nome="Bob", email="bob@example.com", senha_hash="hash", role="USER", ...)
    E chamo usuario_repository.buscar_por_id com o id retornado
    Então retorna o usuário com email "bob@example.com"

  Cenário: buscar_por_email retorna o usuário correto
    Dado que existe um usuário com email "carol@example.com"
    Quando chamo usuario_repository.buscar_por_email("carol@example.com")
    Então retorna o usuário com email "carol@example.com"

  Cenário: buscar_por_email com email inexistente retorna None
    Dado que não existe nenhum usuário com email "desconhecido@example.com"
    Quando chamo usuario_repository.buscar_por_email("desconhecido@example.com")
    Então retorna None

  Cenário: criar usuário com email duplicado falha
    Dado que existe um usuário com email "duplicado@example.com"
    Quando chamo usuario_repository.criar com email "duplicado@example.com"
    Então a operação falha com erro de unicidade

  Cenário: listar usuários retorna todos os registros
    Dado que existem 4 usuários no banco
    Quando chamo usuario_repository.listar()
    Então o resultado contém exatamente 4 usuários

  Cenário: atualizar dados do usuário persiste as mudanças
    Dado que existe o usuário id=5 com nome "Antigo"
    Quando chamo usuario_repository.atualizar(id=5, nome="Novo")
    E chamo usuario_repository.buscar_por_id(5)
    Então o nome retornado é "Novo"

  Cenário: excluir usuário remove o registro
    Dado que existe o usuário id=7
    Quando chamo usuario_repository.excluir(id=7)
    E chamo usuario_repository.buscar_por_id(7)
    Então retorna None
