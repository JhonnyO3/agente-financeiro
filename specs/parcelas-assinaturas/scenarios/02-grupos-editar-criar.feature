# language: pt
Funcionalidade: Grupos de parcelas — editar (PUT) e criar (POST) (T02)
  Service e controller de grupos. Contratos: api-grupos.md, repositorio-grupos.md,
  datas-parcela.md.

  # ---------------------------------------------------------------------------
  # PUT /api/grupos/{grupo_parcela_id} — editar grupo (RF-01)
  # ---------------------------------------------------------------------------

  Cenário: Editar título altera descricao de todas as linhas do grupo (pagas e pendentes)
    Dado um grupo "grp-aaa" com 4 parcelas: 1-2 PAGO, 3-4 PENDENTE, do usuário 1
    Quando PUT /api/grupos/grp-aaa com body {"descricao": "Novo título", "valor_parcela": "150.00", "proxima_data": "2026-07-10", "parcela_atual": 3, "parcela_total": 4}
    Então o status HTTP é 200
    E o corpo contém {"ok": true, "grupo_parcela_id": "grp-aaa", "parcela_total": 4}
    E todas as 4 linhas do grupo têm descricao="Novo título"

  Cenário: Editar valor atualiza só as parcelas PENDENTE; PAGO permanecem intactas
    Dado um grupo "grp-bbb" com 4 parcelas: 1-2 PAGO (valor 100.00), 3-4 PENDENTE, do usuário 1
    Quando PUT /api/grupos/grp-bbb com valor_parcela="200.00" e demais campos válidos
    Então as parcelas 1 e 2 ainda têm valor 100.00
    E as parcelas 3 e 4 têm valor 200.00

  Cenário: Editar data move a próxima pendente e recalcula as seguintes mês a mês
    Dado um grupo "grp-ccc" com parcelas 3 e 4 PENDENTE, do usuário 1
    Quando PUT /api/grupos/grp-ccc com proxima_data="2026-08-05" e parcela_atual=3
    Então a parcela 3 tem data 2026-08-05
    E a parcela 4 tem data 2026-09-05
    E as parcelas PAGO permanecem com suas datas originais

  Cenário: Editar data com dia 31 clampeia meses curtos na cadeia
    Dado um grupo "grp-ddd" com parcelas 1 e 2 PENDENTE, do usuário 1
    Quando PUT /api/grupos/grp-ddd com proxima_data="2026-01-31" e parcela_atual=1
    Então a parcela 1 tem data 2026-01-31
    E a parcela 2 tem data 2026-02-28

  Cenário: parcela_atual=N marca 1..N-1 como PAGO e N..total como PENDENTE
    Dado um grupo "grp-eee" com 5 parcelas todas PENDENTE, do usuário 1
    Quando PUT /api/grupos/grp-eee com parcela_atual=3 e parcela_total=5
    Então as parcelas 1 e 2 têm status PAGO
    E as parcelas 3, 4 e 5 têm status PENDENTE

  Cenário: Aumentar parcela_total cria linhas novas com mesmo grupo e datas contínuas
    Dado um grupo "grp-fff" com 3 parcelas (parcela_total=3), parcela_atual=2, do usuário 1
    E a linha existente tem embedding=[0.1, 0.2, ...], categoria=COMPRAS, forma=CARTAO_CREDITO
    Quando PUT /api/grupos/grp-fff com parcela_total=5 e proxima_data="2026-07-10"
    Então o grupo passa a ter 5 linhas com o mesmo grupo_parcela_id="grp-fff"
    E as linhas 4 e 5 têm embedding copiado do grupo
    E a linha 4 tem data 2026-09-10 (proxima_data + 2 meses)
    E a linha 5 tem data 2026-10-10
    E as linhas 4 e 5 têm categoria=COMPRAS e forma=CARTAO_CREDITO
    E o parcela_total de todas as 5 linhas é 5

  Cenário: Diminuir parcela_total remove as linhas finais e atualiza parcela_total
    Dado um grupo "grp-ggg" com 5 parcelas (parcela_total=5), parcela_atual=2, do usuário 1
    Quando PUT /api/grupos/grp-ggg com parcela_total=3 e parcela_atual=2
    Então as parcelas 4 e 5 são excluídas do banco
    E as 3 linhas restantes têm parcela_total=3

  # ---------------------------------------------------------------------------
  # Erros 400 — PUT /api/grupos
  # ---------------------------------------------------------------------------

  Cenário: ID malformado retorna 400 com "ID inválido"
    Dado que o usuário 1 está autenticado
    Quando PUT /api/grupos/nao-e-uuid com body completo válido
    Então o status HTTP é 400
    E o corpo contém {"erro": "ID inválido"}

  Cenário: parcela_total menor que parcela_atual retorna 400
    Dado um grupo "grp-hhh" do usuário 1 com 5 parcelas
    Quando PUT /api/grupos/grp-hhh com parcela_total=2 e parcela_atual=3
    Então o status HTTP é 400
    E o corpo de erro contém o campo "erro"

  Cenário: valor_parcela igual a zero retorna 400
    Dado um grupo "grp-iii" do usuário 1
    Quando PUT /api/grupos/grp-iii com valor_parcela="0.00"
    Então o status HTTP é 400
    E o corpo de erro contém o campo "erro"

  Cenário: valor_parcela negativo retorna 400
    Dado um grupo "grp-iii" do usuário 1
    Quando PUT /api/grupos/grp-iii com valor_parcela="-10.00"
    Então o status HTTP é 400
    E o corpo de erro contém o campo "erro"

  Cenário: Campo descricao ausente retorna 400 com lista de campos ausentes
    Dado que o usuário 1 está autenticado
    Quando PUT /api/grupos/grp-jjj sem o campo descricao no body
    Então o status HTTP é 400
    E o corpo contém {"erro": "Campos obrigatorios ausentes: descricao"}

  Cenário: Campo proxima_data ausente retorna 400 com lista de campos ausentes
    Dado que o usuário 1 está autenticado
    Quando PUT /api/grupos/grp-jjj sem o campo proxima_data no body
    Então o status HTTP é 400
    E o corpo contém chave "erro" com menção a "proxima_data"

  # ---------------------------------------------------------------------------
  # Erro 404 — PUT /api/grupos
  # ---------------------------------------------------------------------------

  Cenário: Grupo inexistente retorna 404
    Dado que não existe nenhum grupo com ID "grp-zzz"
    Quando PUT /api/grupos/grp-zzz com body completo válido pelo usuário 1
    Então o status HTTP é 404
    E o corpo contém {"erro": "Grupo nao encontrado"}

  Cenário: Grupo de outro usuário retorna 404
    Dado um grupo "grp-kkk" pertencente ao usuário 2
    Quando PUT /api/grupos/grp-kkk com body válido pelo usuário 1
    Então o status HTTP é 404
    E o corpo contém {"erro": "Grupo nao encontrado"}

  # ---------------------------------------------------------------------------
  # POST /api/grupos — criar parcelamento (RF-02)
  # ---------------------------------------------------------------------------

  Cenário: Criar 12 parcelas de R$100 gera 12 linhas com o mesmo grupo_parcela_id
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos com {"descricao": "Notebook", "valor_parcela": "100.00", "parcela_total": 12, "parcela_atual": 1, "proxima_data": "2026-07-05"}
    Então o status HTTP é 201
    E o corpo contém {"ok": true} e "grupo_parcela_id" e "parcela_total": 12
    E existem 12 linhas no banco com o mesmo grupo_parcela_id gerado
    E todas as 12 linhas têm valor=100.00, tipo=GASTO, recorrente=False, embedding=None

  Cenário: parcela_atual=4 marca parcelas 1-3 como PAGO e 4-12 como PENDENTE
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos com parcela_total=12, parcela_atual=4, proxima_data="2026-07-05" e valor_parcela="100.00"
    Então as parcelas 1, 2 e 3 têm status PAGO
    E as parcelas 4 a 12 têm status PENDENTE

  Cenário: Datas seguem cadeia mensal ancorada na proxima_data
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos com parcela_total=3, parcela_atual=1, proxima_data="2026-07-10"
    Então a parcela 1 tem data 2026-07-10
    E a parcela 2 tem data 2026-08-10
    E a parcela 3 tem data 2026-09-10

  Cenário: parcela_atual default é 1 quando omitido
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos com parcela_total=3 e proxima_data="2026-07-10" sem campo parcela_atual
    Então a parcela 1 tem status PENDENTE
    E nenhuma parcela tem status PAGO

  Cenário: Defaults aplicados quando categoria e forma_pagamento são omitidos
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos com campos obrigatórios e sem categoria e sem forma_pagamento
    Então todas as linhas têm categoria=COMPRAS
    E todas as linhas têm forma_pagamento=CARTAO_CREDITO

  # ---------------------------------------------------------------------------
  # Erros 400 — POST /api/grupos
  # ---------------------------------------------------------------------------

  Cenário: parcela_total menor que 2 retorna 400
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos com parcela_total=1
    Então o status HTTP é 400
    E o corpo de erro contém o campo "erro"

  Cenário: valor_parcela igual a zero retorna 400 no POST
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos com valor_parcela="0.00" e parcela_total=3
    Então o status HTTP é 400
    E o corpo de erro contém o campo "erro"

  Cenário: valor_parcela negativo retorna 400 no POST
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos com valor_parcela="-50.00" e parcela_total=3
    Então o status HTTP é 400
    E o corpo de erro contém o campo "erro"

  Cenário: Campo descricao ausente retorna 400 no POST
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos sem o campo descricao
    Então o status HTTP é 400
    E o corpo contém chave "erro" com menção a "descricao"

  Cenário: Campo proxima_data ausente retorna 400 no POST
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos sem o campo proxima_data
    Então o status HTTP é 400
    E o corpo contém chave "erro" com menção a "proxima_data"

  Cenário: Campo valor_parcela ausente retorna 400 no POST
    Dado que o usuário 1 está autenticado
    Quando POST /api/grupos sem o campo valor_parcela
    Então o status HTTP é 400
    E o corpo contém chave "erro" com menção a "valor_parcela"
