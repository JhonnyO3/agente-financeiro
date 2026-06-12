# language: pt
Funcionalidade: UI — editar e criar parcelamento no dashboard (T05)
  Cards com botão Editar e atributos data-*, modal reutilizável #modal-grupo, e JS
  que chama POST/PUT via proxy e recarrega a seção. Contrato: frontend-dashboard.md,
  api-grupos.md.

  # ---------------------------------------------------------------------------
  # Renderização dos cards — botão Editar e data-*
  # ---------------------------------------------------------------------------

  Cenário: Card de parcela renderiza botão Editar com todos os data-* do contrato
    Dado que a seção "Parcelas em andamento" exibe um card para o grupo "grp-aaa"
    E os dados do grupo são: descricao="Notebook", valor="150.00", parcela_atual=3, parcela_total=6, proxima_data="2026-07-10"
    Quando a função carregarParcelas() injeta o card no DOM
    Então o botão .btn-editar-grupo do card tem data-grupo="grp-aaa"
    E tem data-descricao="Notebook"
    E tem data-valor="150.00"
    E tem data-parcela-atual="3"
    E tem data-parcela-total="6"
    E tem data-proxima-data="2026-07-10"

  Cenário: Todos os cards da seção recebem botão .btn-editar-grupo
    Dado que a listagem retorna 3 grupos de parcelas
    Quando a função carregarParcelas() injeta os cards
    Então o DOM contém 3 elementos com a classe .btn-editar-grupo

  # ---------------------------------------------------------------------------
  # Botão "+ Novo parcelamento" — modo criar
  # ---------------------------------------------------------------------------

  Cenário: Clicar em #btn-novo-parcelamento abre o modal em modo criar (campos vazios)
    Dado que a página do dashboard está carregada
    Quando o usuário clica em #btn-novo-parcelamento
    Então o #modal-grupo é exibido
    E o campo #grupo-id está vazio
    E o campo #grupo-descricao está vazio
    E o campo #grupo-valor está vazio
    E o campo #grupo-parcela-atual está vazio
    E o campo #grupo-parcela-total está vazio
    E o campo #grupo-proxima-data está vazio
    E o campo #grupo-erro está vazio

  # ---------------------------------------------------------------------------
  # Botão Editar — modo editar (campos preenchidos pelos data-*)
  # ---------------------------------------------------------------------------

  Cenário: Clicar em .btn-editar-grupo preenche o modal com os dados do card
    Dado um card com data-grupo="grp-bbb", data-descricao="Smartphone", data-valor="200.00", data-parcela-atual="2", data-parcela-total="5", data-proxima-data="2026-08-01"
    Quando o usuário clica no botão .btn-editar-grupo desse card
    Então o #modal-grupo é exibido
    E o campo #grupo-id contém "grp-bbb"
    E o campo #grupo-descricao contém "Smartphone"
    E o campo #grupo-valor contém "200.00"
    E o campo #grupo-parcela-atual contém "2"
    E o campo #grupo-parcela-total contém "5"
    E o campo #grupo-proxima-data contém "2026-08-01"

  # ---------------------------------------------------------------------------
  # Salvar — modo criar (POST)
  # ---------------------------------------------------------------------------

  Cenário: Salvar em modo criar chama POST /api/grupos com os valores do formulário
    Dado que o #modal-grupo está aberto em modo criar (grupo-id vazio)
    E os campos estão preenchidos: descricao="TV", valor="300.00", parcela_total=6, parcela_atual=1, proxima_data="2026-07-15", categoria="ELETRONICOS", forma_pagamento="CARTAO_CREDITO"
    Quando o usuário clica em #btn-salvar-grupo
    Então é feito um POST para /api/grupos com o payload correto
    E o #modal-grupo é fechado
    E carregarParcelas() é chamado para recarregar a seção sem reload da página

  Cenário: Salvar criar sem aritmética monetária no JS
    Dado que o campo #grupo-valor contém a string "100.00"
    Quando grupos.js monta o payload para POST /api/grupos
    Então o campo valor_parcela do payload é a string "100.00" sem transformação numérica

  # ---------------------------------------------------------------------------
  # Salvar — modo editar (PUT)
  # ---------------------------------------------------------------------------

  Cenário: Salvar em modo editar chama PUT /api/grupos/{id} com os valores do formulário
    Dado que o #modal-grupo está aberto em modo editar com #grupo-id="grp-ccc"
    E os campos estão preenchidos: descricao="Notebook Pro", valor="500.00", parcela_total=4, parcela_atual=2, proxima_data="2026-08-10"
    Quando o usuário clica em #btn-salvar-grupo
    Então é feito um PUT para /api/grupos/grp-ccc com o payload correto
    E carregarParcelas() é chamado para recarregar a seção

  # ---------------------------------------------------------------------------
  # Recarregar seção sem reload da página
  # ---------------------------------------------------------------------------

  Cenário: Após salvar com sucesso a seção é atualizada sem reload da página completa
    Dado que o POST /api/grupos retornou 201 com sucesso
    Quando grupos.js processa a resposta
    Então a função carregarParcelas() é invocada
    E window.location.reload() não é chamado

  # ---------------------------------------------------------------------------
  # Exibição de erros do backend em #grupo-erro
  # ---------------------------------------------------------------------------

  Cenário: Erro 400 do backend é exibido em #grupo-erro
    Dado que o #modal-grupo está aberto em modo criar
    E o backend retorna 400 {"erro": "Campos obrigatorios ausentes: descricao"}
    Quando o usuário clica em #btn-salvar-grupo
    Então o elemento #grupo-erro exibe o texto "Campos obrigatorios ausentes: descricao"
    E o #modal-grupo permanece aberto

  Cenário: Erro 404 do backend é exibido em #grupo-erro no modo editar
    Dado que o #modal-grupo está aberto em modo editar com #grupo-id="grp-zzz"
    E o backend retorna 404 {"erro": "Grupo nao encontrado"}
    Quando o usuário clica em #btn-salvar-grupo
    Então o elemento #grupo-erro exibe o texto "Grupo nao encontrado"
    E o #modal-grupo permanece aberto

  Cenário: #grupo-erro é limpo ao abrir o modal novamente
    Dado que o #grupo-erro exibe uma mensagem de erro anterior
    Quando o usuário clica em #btn-novo-parcelamento ou .btn-editar-grupo
    Então o #grupo-erro está vazio
