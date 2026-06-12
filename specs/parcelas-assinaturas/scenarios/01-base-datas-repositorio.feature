# language: pt
Funcionalidade: Helpers de data de parcelas e métodos de repositório (T01)
  Base compartilhada por grupos e gastos fixos: funções puras de data no backend,
  métodos novos de repositório e ajuste de listar_ativas. Contratos: datas-parcela.md
  e repositorio-grupos.md.

  # ---------------------------------------------------------------------------
  # adicionar_meses — clamp de fim de mês
  # ---------------------------------------------------------------------------

  Cenário: adicionar_meses em mês com dia existente
    Dado a data 2026-03-15
    Quando se chama adicionar_meses com 1 mês
    Então o resultado é 2026-04-15

  Cenário: adicionar_meses clampeia dia 31 para fim de fevereiro (não bissexto)
    Dado a data 2026-01-31
    Quando se chama adicionar_meses com 1 mês
    Então o resultado é 2026-02-28

  Cenário: adicionar_meses clampeia dia 31 para fim de abril
    Dado a data 2026-03-31
    Quando se chama adicionar_meses com 1 mês
    Então o resultado é 2026-04-30

  Cenário: adicionar_meses com meses negativos recua no tempo
    Dado a data 2026-03-31
    Quando se chama adicionar_meses com -1 mês
    Então o resultado é 2026-02-28

  Cenário: adicionar_meses preserva dia em fevereiro bissexto
    Dado a data 2024-01-29
    Quando se chama adicionar_meses com 1 mês
    Então o resultado é 2024-02-29

  # ---------------------------------------------------------------------------
  # status_por_data
  # ---------------------------------------------------------------------------

  Cenário: status_por_data retorna PAGO para data passada
    Dado que hoje é 2026-06-12
    Quando se chama status_por_data com a data 2026-06-11
    Então o status retornado é "PAGO"

  Cenário: status_por_data retorna PENDENTE para hoje
    Dado que hoje é 2026-06-12
    Quando se chama status_por_data com a data 2026-06-12
    Então o status retornado é "PENDENTE"

  Cenário: status_por_data retorna PENDENTE para data futura
    Dado que hoje é 2026-06-12
    Quando se chama status_por_data com a data 2026-07-01
    Então o status retornado é "PENDENTE"

  # ---------------------------------------------------------------------------
  # datas_do_grupo — cadeia ancorada na parcela atual
  # ---------------------------------------------------------------------------

  Cenário: datas_do_grupo com parcela_atual=1 gera cadeia crescente
    Dado data_parcela_atual=2026-06-05, parcela_atual=1, parcela_total=3
    Quando se chama datas_do_grupo
    Então a lista retornada contém [2026-06-05, 2026-07-05, 2026-08-05]

  Cenário: datas_do_grupo ancora a parcela atual e recua as anteriores
    Dado data_parcela_atual=2026-06-05, parcela_atual=3, parcela_total=5
    Quando se chama datas_do_grupo
    Então a lista retornada contém [2026-04-05, 2026-05-05, 2026-06-05, 2026-07-05, 2026-08-05]

  Cenário: datas_do_grupo clampeia data de retrocesso em mês curto
    Dado data_parcela_atual=2026-03-31, parcela_atual=2, parcela_total=3
    Quando se chama datas_do_grupo
    Então a lista retornada contém [2026-02-28, 2026-03-31, 2026-04-30]

  Cenário: datas_do_grupo retorna lista com parcela_total elementos
    Dado data_parcela_atual=2026-06-10, parcela_atual=2, parcela_total=6
    Quando se chama datas_do_grupo
    Então a lista retornada tem exatamente 6 elementos
    E o elemento de índice 1 (parcela 2) é 2026-06-10

  # ---------------------------------------------------------------------------
  # buscar_por_grupo_com_embedding
  # ---------------------------------------------------------------------------

  Cenário: buscar_por_grupo_com_embedding carrega embedding sem query extra
    Dado um grupo "abc-111" com 3 parcelas pertencentes ao usuário 1
    E o campo embedding é deferred no ORM
    Quando se chama buscar_por_grupo_com_embedding com grupo_parcela_id="abc-111" e usuario_id=1
    Então as 3 linhas são retornadas com embedding não nulo carregado
    E as linhas estão ordenadas por parcela_numero crescente

  Cenário: buscar_por_grupo_com_embedding filtra por usuario_id
    Dado um grupo "abc-111" pertencente ao usuário 2
    Quando se chama buscar_por_grupo_com_embedding com grupo_parcela_id="abc-111" e usuario_id=1
    Então a lista retornada é vazia

  Cenário: buscar_por_grupo_com_embedding sem usuario_id retorna o grupo independente do dono
    Dado um grupo "abc-111" com 2 parcelas pertencentes ao usuário 5
    Quando se chama buscar_por_grupo_com_embedding com grupo_parcela_id="abc-111" sem usuario_id
    Então as 2 linhas são retornadas

  # ---------------------------------------------------------------------------
  # listar_recorrentes
  # ---------------------------------------------------------------------------

  Cenário: listar_recorrentes retorna só linhas recorrente=True do usuário
    Dado que o usuário 1 tem 2 transações com recorrente=True e 1 com recorrente=False
    Quando se chama listar_recorrentes com usuario_id=1
    Então a lista retornada tem 2 itens, todos com recorrente=True

  Cenário: listar_recorrentes isola por usuario_id
    Dado que o usuário 2 tem 3 transações com recorrente=True
    Quando se chama listar_recorrentes com usuario_id=1
    Então a lista retornada é vazia

  Cenário: listar_recorrentes ordena por data
    Dado que o usuário 1 tem recorrentes com data 2026-06-15, 2026-06-05 e 2026-06-20
    Quando se chama listar_recorrentes com usuario_id=1
    Então a ordem das datas retornadas é [2026-06-05, 2026-06-15, 2026-06-20]

  # ---------------------------------------------------------------------------
  # excluir_por_grupo_e_numeros
  # ---------------------------------------------------------------------------

  Cenário: excluir_por_grupo_e_numeros remove só os parcela_numero listados
    Dado um grupo "grp-999" com parcelas 1, 2, 3, 4 e 5 do usuário 1
    Quando se chama excluir_por_grupo_e_numeros com grupo="grp-999", numeros=[4,5], usuario_id=1
    Então o rowcount retornado é 2
    E as parcelas 1, 2 e 3 permanecem no banco

  Cenário: excluir_por_grupo_e_numeros respeita usuario_id
    Dado um grupo "grp-999" com parcelas 1, 2 pertencentes ao usuário 2
    Quando se chama excluir_por_grupo_e_numeros com grupo="grp-999", numeros=[1,2], usuario_id=1
    Então o rowcount retornado é 0
    E as parcelas do usuário 2 permanecem intactas

  Cenário: excluir_por_grupo_e_numeros retorna 0 para lista vazia de numeros
    Dado um grupo "grp-999" com parcelas 1 e 2 do usuário 1
    Quando se chama excluir_por_grupo_e_numeros com numeros=[]
    Então o rowcount retornado é 0

  # ---------------------------------------------------------------------------
  # listar_ativas — pendente vencida incluída; grupo quitado excluído
  # ---------------------------------------------------------------------------

  Cenário: listar_ativas inclui grupo com parcela pendente vencida
    Dado um grupo de 3 parcelas onde a pendente tem data 2026-05-01 (passado)
    Quando se chama listar_ativas
    Então o grupo aparece na listagem

  Cenário: listar_ativas exclui grupo totalmente pago
    Dado um grupo de 3 parcelas onde todas têm status PAGO
    Quando se chama listar_ativas
    Então o grupo não aparece na listagem

  Cenário: listar_ativas exclui transação com parcela_total=1 (não é grupo de parcelas)
    Dado uma transação com parcela_total=1 e status PENDENTE
    Quando se chama listar_ativas
    Então a transação não aparece na listagem
