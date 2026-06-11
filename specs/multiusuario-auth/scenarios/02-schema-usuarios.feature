# language: pt
Funcionalidade: Schema da tabela usuarios e vínculo usuario_id em transacoes

  Como sistema multiusuário
  Quero uma tabela usuarios com constraints corretas e um vínculo FK em transacoes
  Para que cada transação pertença a um usuário e dados sejam isolados por dono

  Contexto:
    Dado que a tarefa 01 (separação de módulos) foi concluída
    E o ORM backend/models/usuario.py e backend/models/enums.py existem

  Cenário: Migration cria a tabela usuarios com email único
    Dado que a migration de 3 fases é aplicada em um banco vazio de transacoes
    Quando inspeciono a tabela usuarios
    Então existe a constraint UNIQUE na coluna email
    E a coluna email é NOT NULL

  Cenário: Inserir dois usuários com o mesmo email falha
    Dado que existe um usuário com email "alice@example.com"
    Quando tento inserir outro usuário com email "alice@example.com"
    Então a operação falha com erro de unicidade (unique constraint violation)

  Cenário: Telefone é único quando preenchido
    Dado que existe um usuário com telefone "11999990001"
    Quando tento inserir outro usuário com telefone "11999990001"
    Então a operação falha com erro de unicidade

  Cenário: Múltiplos usuários com telefone nulo são permitidos
    Dado que existem dois usuários sem telefone (telefone = NULL)
    Quando inspeciono a tabela usuarios
    Então ambos os registros coexistem sem erro de unicidade

  Cenário: Role padrão é USER quando não informado
    Dado que crio um usuário sem especificar role
    Quando consulto o registro criado
    Então o campo role é "USER"

  Cenário: Role pode ser definido como ADMIN
    Dado que crio um usuário com role "ADMIN"
    Quando consulto o registro criado
    Então o campo role é "ADMIN"

  Cenário: Role aceita apenas ADMIN ou USER
    Dado que tento criar um usuário com role "SUPERUSER"
    Quando a operação é executada
    Então a operação falha com erro de validação de enum

  Cenário: Coluna senha_hash existe e senha em texto puro não existe
    Dado que a migration foi aplicada
    Quando inspeciono as colunas da tabela usuarios
    Então existe a coluna "senha_hash"
    E não existe nenhuma coluna chamada "senha" ou "password"

  Cenário: Migration de backfill insere usuário Jhonatas com placeholder sem senha utilizável
    Dado que existiam transações no banco antes da migration
    Quando a migration de backfill é aplicada
    Então existe um registro na tabela usuarios com email "jhonatas2004@gmail.com" e role "ADMIN"
    E o campo senha_hash desse registro contém um placeholder que não autentica nenhuma senha real

  Cenário: Após backfill nenhuma transacao tem usuario_id nulo
    Dado que existiam transações sem usuario_id antes da migration
    Quando a migration de 3 fases é aplicada completamente
    Então SELECT COUNT(*) FROM transacoes WHERE usuario_id IS NULL retorna 0

  Cenário: Coluna usuario_id em transacoes é NOT NULL após a migration
    Dado que a migration de 3 fases foi aplicada
    Quando inspeciono a definição da coluna usuario_id em transacoes
    Então a coluna é NOT NULL
    E possui ForeignKey referenciando usuarios.id com ON DELETE CASCADE

  Cenário: Fase not-null não pode preceder o backfill
    Dado que a migration fase 1 (nullable) foi aplicada
    E a migration fase 2 (backfill) ainda não foi aplicada
    Quando tento aplicar diretamente a migration fase 3 (NOT NULL) com transações existentes
    Então a operação falha porque há linhas com usuario_id nulo

  Cenário: Migration não grava senha utilizável para o Jhonatas
    Dado que a migration de backfill criou o usuário Jhonatas
    Quando tento autenticar com email "jhonatas2004@gmail.com" e qualquer senha antes de rodar o script
    Então a autenticação falha (hash placeholder não verifica)
