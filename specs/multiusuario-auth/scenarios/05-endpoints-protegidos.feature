# language: pt
Funcionalidade: Endpoints de dados protegidos e filtrados por usuario_id

  Como usuário autenticado do dashboard
  Quero que todos os endpoints de dados exijam Bearer e retornem apenas meus próprios dados
  Para que nenhum usuário acesse dados de outro

  Contexto:
    Dado que as tarefas 03 e 04 foram concluídas
    E existe o usuário Alice (id=1) com access_token válido
    E existe o usuário Bob (id=2) com access_token válido
    E Alice tem 3 transações cadastradas
    E Bob tem 2 transações cadastradas

  # ---------------------------------------------------------------------------
  # Proteção — sem Bearer
  # ---------------------------------------------------------------------------

  Cenário: GET /api/transacoes sem Bearer retorna 401
    Quando faço GET /api/transacoes sem header Authorization
    Então a resposta tem status 401
    E o body contém {"erro": "não autenticado"}

  Cenário: GET /api/resumo sem Bearer retorna 401
    Quando faço GET /api/resumo?periodo=2026-06 sem header Authorization
    Então a resposta tem status 401

  Cenário: GET /api/grafico/categorias sem Bearer retorna 401
    Quando faço GET /api/grafico/categorias?periodo=2026-06 sem header Authorization
    Então a resposta tem status 401

  Cenário: GET /api/grafico/mensal sem Bearer retorna 401
    Quando faço GET /api/grafico/mensal sem header Authorization
    Então a resposta tem status 401

  Cenário: GET /api/grafico/evolucao sem Bearer retorna 401
    Quando faço GET /api/grafico/evolucao sem header Authorization
    Então a resposta tem status 401

  Cenário: GET /api/parcelas-ativas sem Bearer retorna 401
    Quando faço GET /api/parcelas-ativas sem header Authorization
    Então a resposta tem status 401

  Cenário: GET /api/projecao sem Bearer retorna 401
    Quando faço GET /api/projecao sem header Authorization
    Então a resposta tem status 401

  Cenário: DELETE /api/grupos/{grupo} sem Bearer retorna 401
    Quando faço DELETE /api/grupos/grupo-xyz sem header Authorization
    Então a resposta tem status 401

  Cenário: GET /health permanece público sem necessidade de Bearer
    Quando faço GET /health sem header Authorization
    Então a resposta tem status 200

  # ---------------------------------------------------------------------------
  # Isolamento entre usuários — GET /api/transacoes
  # ---------------------------------------------------------------------------

  Cenário: Alice vê apenas as próprias transações em GET /api/transacoes
    Quando Alice faz GET /api/transacoes com seu Bearer
    Então a resposta tem status 200
    E o body contém exatamente 3 transações
    E nenhuma transação pertence ao usuário 2 (Bob)

  Cenário: Bob vê apenas as próprias transações em GET /api/transacoes
    Quando Bob faz GET /api/transacoes com seu Bearer
    Então a resposta tem status 200
    E o body contém exatamente 2 transações
    E nenhuma transação pertence ao usuário 1 (Alice)

  Cenário: Shape JSON de GET /api/transacoes permanece idêntico ao anterior à proteção
    Quando Alice faz GET /api/transacoes com seu Bearer
    Então o shape do JSON de resposta (chaves e formato) é byte-idêntico ao shape anterior à feature

  # ---------------------------------------------------------------------------
  # POST /api/transacoes — usuario_id do body é ignorado
  # ---------------------------------------------------------------------------

  Cenário: POST /api/transacoes usa usuario_id do token, ignora body
    Dado que Alice envia POST /api/transacoes com body contendo usuario_id=2 (Bob)
    Quando a requisição é processada com o Bearer de Alice
    Então a transação criada tem usuario_id = 1 (Alice)
    E nenhuma transação é criada para o usuário 2 (Bob)

  Cenário: POST /api/transacoes sem Bearer retorna 401
    Quando envio POST /api/transacoes sem header Authorization
    Então a resposta tem status 401

  # ---------------------------------------------------------------------------
  # PUT /api/transacoes/{id} — isolamento de dono
  # ---------------------------------------------------------------------------

  Cenário: Alice edita a própria transação com sucesso
    Dado que a transação id=10 pertence a Alice
    Quando Alice faz PUT /api/transacoes/10 com seu Bearer e dados válidos
    Então a resposta tem status 200
    E a transação id=10 é atualizada

  Cenário: Alice tenta editar transação de Bob e recebe 404
    Dado que a transação id=20 pertence a Bob
    Quando Alice faz PUT /api/transacoes/20 com o Bearer de Alice
    Então a resposta tem status 404
    E a transação id=20 não é alterada

  # ---------------------------------------------------------------------------
  # DELETE /api/transacoes/{id} — isolamento de dono
  # ---------------------------------------------------------------------------

  Cenário: Alice exclui a própria transação com sucesso
    Dado que a transação id=11 pertence a Alice
    Quando Alice faz DELETE /api/transacoes/11 com seu Bearer
    Então a resposta tem status 200
    E a transação id=11 não existe mais no banco

  Cenário: Alice tenta excluir transação de Bob e recebe 404
    Dado que a transação id=21 pertence a Bob
    Quando Alice faz DELETE /api/transacoes/21 com o Bearer de Alice
    Então a resposta tem status 404
    E a transação id=21 ainda existe no banco

  # ---------------------------------------------------------------------------
  # DELETE /api/grupos/{grupo} — isolamento de dono
  # ---------------------------------------------------------------------------

  Cenário: Alice exclui grupo de parcelas próprio com sucesso
    Dado que o grupo "grupo-alice" tem parcelas pertencentes a Alice
    Quando Alice faz DELETE /api/grupos/grupo-alice com seu Bearer
    Então a resposta tem status 200
    E as parcelas do grupo "grupo-alice" são removidas

  Cenário: Alice tenta excluir grupo de parcelas de Bob e recebe 404
    Dado que o grupo "grupo-bob" tem parcelas pertencentes a Bob
    Quando Alice faz DELETE /api/grupos/grupo-bob com o Bearer de Alice
    Então a resposta tem status 404
    E as parcelas do grupo "grupo-bob" permanecem intactas

  # ---------------------------------------------------------------------------
  # Isolamento em endpoints agregados
  # ---------------------------------------------------------------------------

  Cenário: GET /api/resumo retorna apenas dados de Alice
    Dado que Alice tem gastos em Jun/2026 e Bob também tem gastos em Jun/2026
    Quando Alice faz GET /api/resumo?periodo=2026-06 com seu Bearer
    Então os totais do resumo refletem apenas as transações de Alice

  Cenário: GET /api/parcelas-ativas retorna apenas parcelas de Alice
    Dado que Alice tem 2 parcelas ativas e Bob tem 3 parcelas ativas
    Quando Alice faz GET /api/parcelas-ativas com seu Bearer
    Então a resposta contém exatamente 2 parcelas
    E nenhuma parcela pertence a Bob

  Cenário: GET /api/projecao retorna apenas projeção de Alice
    Quando Alice faz GET /api/projecao com seu Bearer
    Então a projeção é calculada apenas com as transações de Alice
