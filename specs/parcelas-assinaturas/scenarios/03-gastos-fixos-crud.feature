# language: pt
Funcionalidade: Gastos fixos — CRUD (GET/POST/PUT/DELETE) (T03)
  Service e controller de gastos fixos sobre linhas recorrente=TRUE.
  Contrato: api-gastos-fixos.md, repositorio-grupos.md.

  # ---------------------------------------------------------------------------
  # GET /api/gastos-fixos — listar (RF-03)
  # ---------------------------------------------------------------------------

  Cenário: Listar retorna só transações recorrente=True do usuário autenticado
    Dado que o usuário 1 tem 2 transações com recorrente=True e 3 com recorrente=False
    E o usuário 2 tem 1 transação com recorrente=True
    Quando GET /api/gastos-fixos pelo usuário 1
    Então o status HTTP é 200
    E o corpo contém 2 itens em "itens"
    E nenhum item pertence ao usuário 2

  Cenário: Listar retorna campos corretos para cada item
    Dado que o usuário 1 tem um gasto fixo: id=12, descricao="Claude", valor=100.00, data=2026-06-05, categoria=GASTOS_FIXOS, forma_pagamento=CARTAO_CREDITO, responsavel="Jhonatas", status=PENDENTE
    Quando GET /api/gastos-fixos pelo usuário 1
    Então o item retornado contém {"id": 12, "descricao": "Claude", "valor": "100.00", "dia_vencimento": 5, "data": "2026-06-05", "categoria": "GASTOS_FIXOS", "forma_pagamento": "CARTAO_CREDITO", "responsavel": "Jhonatas", "status": "PENDENTE"}

  Cenário: Listar ordena os itens por dia_vencimento crescente
    Dado que o usuário 1 tem gastos fixos com dia_vencimento 15, 5 e 20
    Quando GET /api/gastos-fixos pelo usuário 1
    Então a ordem dos dia_vencimento retornados é [5, 15, 20]

  Cenário: total_mensal é a soma dos valores em Decimal serializada com duas casas
    Dado que o usuário 1 tem gastos fixos com valores 100.00, 49.90 e 29.90
    Quando GET /api/gastos-fixos pelo usuário 1
    Então o campo "total_mensal" do corpo é "179.80"

  Cenário: Lista vazia retorna itens vazio e total_mensal zero
    Dado que o usuário 1 não tem nenhuma transação com recorrente=True
    Quando GET /api/gastos-fixos pelo usuário 1
    Então o status HTTP é 200
    E o corpo é {"itens": [], "total_mensal": "0.00"}

  # ---------------------------------------------------------------------------
  # POST /api/gastos-fixos — incluir (RF-04)
  # ---------------------------------------------------------------------------

  Cenário: Incluir gasto fixo com PIX grava status PAGO
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos com {"descricao": "Academia", "valor": "99.90", "data": "2026-06-10", "forma_pagamento": "PIX"}
    Então o status HTTP é 201
    E o corpo contém {"ok": true} e um campo "id" inteiro
    E a linha gravada tem recorrente=True, parcela_numero=1, parcela_total=1, tipo=GASTO, embedding=None
    E o status da linha é PAGO

  Cenário: Incluir gasto fixo com forma diferente de PIX grava status PENDENTE
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos com {"descricao": "Luz", "valor": "150.00", "data": "2026-06-15", "forma_pagamento": "CARTAO_CREDITO"}
    Então o status HTTP é 201
    E o status da linha gravada é PENDENTE

  Cenário: Defaults aplicados quando categoria e forma_pagamento são omitidos no POST
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos com apenas descricao, valor e data
    Então a linha gravada tem categoria=GASTOS_FIXOS
    E a linha gravada tem forma_pagamento=PIX

  Cenário: Incluir gasto fixo gera grupo_parcela_id novo (UUID)
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos com body válido
    Então a linha gravada tem grupo_parcela_id preenchido com um UUID válido

  # ---------------------------------------------------------------------------
  # Erros 400 — POST /api/gastos-fixos
  # ---------------------------------------------------------------------------

  Cenário: valor igual a zero retorna 400
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos com valor="0.00"
    Então o status HTTP é 400
    E o corpo de erro contém o campo "erro"

  Cenário: valor negativo retorna 400
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos com valor="-10.00"
    Então o status HTTP é 400
    E o corpo de erro contém o campo "erro"

  Cenário: Campo descricao ausente retorna 400 com lista de campos ausentes
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos sem o campo descricao
    Então o status HTTP é 400
    E o corpo contém {"erro": "Campos obrigatorios ausentes: descricao"}

  Cenário: Campo valor ausente retorna 400 com lista de campos ausentes
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos sem o campo valor
    Então o status HTTP é 400
    E o corpo contém chave "erro" com menção a "valor"

  Cenário: Campo data ausente retorna 400 com lista de campos ausentes
    Dado que o usuário 1 está autenticado
    Quando POST /api/gastos-fixos sem o campo data
    Então o status HTTP é 400
    E o corpo contém chave "erro" com menção a "data"

  # ---------------------------------------------------------------------------
  # PUT /api/gastos-fixos/{id} — editar (RF-04)
  # ---------------------------------------------------------------------------

  Cenário: Editar descricao de gasto fixo existente do usuário
    Dado que o usuário 1 tem um gasto fixo com id=7 e descricao="Spotify"
    Quando PUT /api/gastos-fixos/7 com {"descricao": "Spotify Premium"}
    Então o status HTTP é 200
    E o corpo é {"ok": true}
    E a linha id=7 tem descricao="Spotify Premium"

  Cenário: Editar valor de gasto fixo existente
    Dado que o usuário 1 tem um gasto fixo com id=7
    Quando PUT /api/gastos-fixos/7 com {"valor": "29.90"}
    Então o status HTTP é 200
    E a linha id=7 tem valor=29.90

  Cenário: Editar é parcial — campos não enviados permanecem inalterados
    Dado que o usuário 1 tem um gasto fixo com id=8, descricao="Netflix", valor=45.90, categoria=GASTOS_FIXOS
    Quando PUT /api/gastos-fixos/8 com apenas {"valor": "55.90"}
    Então a linha id=8 ainda tem descricao="Netflix" e categoria=GASTOS_FIXOS
    E a linha id=8 tem valor=55.90

  # ---------------------------------------------------------------------------
  # Erros 404 — PUT /api/gastos-fixos
  # ---------------------------------------------------------------------------

  Cenário: PUT em gasto fixo de outro usuário retorna 404
    Dado que a linha id=9 pertence ao usuário 2
    Quando PUT /api/gastos-fixos/9 com body válido pelo usuário 1
    Então o status HTTP é 404
    E o corpo contém {"erro": "Gasto fixo nao encontrado"}

  Cenário: PUT em transação não-recorrente retorna 404
    Dado que a linha id=10 pertence ao usuário 1 mas tem recorrente=False
    Quando PUT /api/gastos-fixos/10 com body válido
    Então o status HTTP é 404
    E o corpo contém {"erro": "Gasto fixo nao encontrado"}

  Cenário: PUT em id inexistente retorna 404
    Dado que não existe nenhuma linha com id=999
    Quando PUT /api/gastos-fixos/999 com body válido pelo usuário 1
    Então o status HTTP é 404
    E o corpo contém {"erro": "Gasto fixo nao encontrado"}

  # ---------------------------------------------------------------------------
  # DELETE /api/gastos-fixos/{id} — remover (RF-04)
  # ---------------------------------------------------------------------------

  Cenário: Remover gasto fixo existente do usuário faz hard delete
    Dado que o usuário 1 tem um gasto fixo com id=5
    Quando DELETE /api/gastos-fixos/5 pelo usuário 1
    Então o status HTTP é 200
    E o corpo é {"ok": true}
    E a linha id=5 não existe mais no banco

  Cenário: DELETE em gasto fixo de outro usuário retorna 404
    Dado que a linha id=6 pertence ao usuário 2
    Quando DELETE /api/gastos-fixos/6 pelo usuário 1
    Então o status HTTP é 404
    E o corpo contém {"erro": "Gasto fixo nao encontrado"}

  Cenário: DELETE em transação não-recorrente retorna 404
    Dado que a linha id=11 pertence ao usuário 1 mas tem recorrente=False
    Quando DELETE /api/gastos-fixos/11
    Então o status HTTP é 404
    E o corpo contém {"erro": "Gasto fixo nao encontrado"}

  Cenário: DELETE em id inexistente retorna 404
    Dado que não existe nenhuma linha com id=888
    Quando DELETE /api/gastos-fixos/888 pelo usuário 1
    Então o status HTTP é 404
    E o corpo contém {"erro": "Gasto fixo nao encontrado"}
