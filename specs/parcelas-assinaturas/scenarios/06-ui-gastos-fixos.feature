# language: pt
Funcionalidade: UI — seção e CRUD de gastos fixos no dashboard (T06)
  Seção "Gastos fixos" com listagem, total mensal (string do backend), modais de
  incluir/editar e confirmação antes de remover. Contrato: frontend-dashboard.md,
  api-gastos-fixos.md.

  # ---------------------------------------------------------------------------
  # Renderização inicial — carregarGastosFixos()
  # ---------------------------------------------------------------------------

  Cenário: Seção renderiza itens vindos do backend ao carregar a página
    Dado que GET /api/gastos-fixos retorna {"itens": [{"id": 1, "descricao": "Netflix", "valor": "45.90", "dia_vencimento": 10, "categoria": "GASTOS_FIXOS", "forma_pagamento": "CARTAO_CREDITO", "responsavel": "Jhonatas", "status": "PENDENTE"}], "total_mensal": "45.90"}
    Quando gastos_fixos.js chama carregarGastosFixos() no DOMContentLoaded
    Então o #gastos-fixos-container exibe 1 item
    E o item exibe descricao="Netflix", valor="45.90", dia_vencimento=10, categoria="GASTOS_FIXOS", forma_pagamento="CARTAO_CREDITO"
    E cada item tem botão .btn-editar-gasto-fixo com data-id="1"
    E cada item tem botão .btn-remover-gasto-fixo com data-id="1"

  Cenário: Total mensal é exibido como string recebida do backend sem somar no JS
    Dado que GET /api/gastos-fixos retorna total_mensal="179.80"
    Quando carregarGastosFixos() é executado
    Então o elemento #gastos-fixos-total exibe o texto "179.80"
    E gastos_fixos.js não realiza nenhuma operação aritmética sobre o valor

  Cenário: Múltiplos itens são ordenados por dia_vencimento conforme ordem recebida do backend
    Dado que GET /api/gastos-fixos retorna 3 itens com dia_vencimento 5, 10 e 20
    Quando carregarGastosFixos() renderiza os itens
    Então os itens aparecem na ordem dia 5, dia 10, dia 20 no DOM

  # ---------------------------------------------------------------------------
  # Estado vazio
  # ---------------------------------------------------------------------------

  Cenário: Lista vazia exibe mensagem "Nenhum gasto fixo cadastrado"
    Dado que GET /api/gastos-fixos retorna {"itens": [], "total_mensal": "0.00"}
    Quando carregarGastosFixos() é executado
    Então o elemento #gastos-fixos-vazio está visível com o texto "Nenhum gasto fixo cadastrado"
    E o #gastos-fixos-container não exibe nenhum item de lista

  Cenário: Estado vazio oculta o elemento #gastos-fixos-vazio quando há itens
    Dado que GET /api/gastos-fixos retorna 2 itens
    Quando carregarGastosFixos() é executado
    Então o elemento #gastos-fixos-vazio está oculto

  # ---------------------------------------------------------------------------
  # Modal incluir — #btn-novo-gasto-fixo
  # ---------------------------------------------------------------------------

  Cenário: Clicar em #btn-novo-gasto-fixo abre o modal em modo criar (campos vazios)
    Dado que a seção "Gastos fixos" está renderizada
    Quando o usuário clica em #btn-novo-gasto-fixo
    Então o #modal-gasto-fixo é exibido
    E o campo #gf-id está vazio
    E o campo #gf-descricao está vazio
    E o campo #gf-valor está vazio
    E o campo #gf-data está vazio
    E o campo #gf-erro está vazio

  Cenário: Salvar novo gasto fixo chama POST /api/gastos-fixos com o payload do formulário
    Dado que o #modal-gasto-fixo está aberto em modo criar (#gf-id vazio)
    E os campos estão preenchidos: descricao="Academia", valor="99.90", data="2026-07-01", categoria="GASTOS_FIXOS", forma_pagamento="PIX"
    Quando o usuário clica em #btn-salvar-gasto-fixo
    Então é feito um POST para /api/gastos-fixos com o payload correto
    E o #modal-gasto-fixo é fechado
    E carregarGastosFixos() é chamado para recarregar a seção sem reload da página

  Cenário: Salvar novo gasto sem aritmética monetária no JS
    Dado que o campo #gf-valor contém a string "99.90"
    Quando gastos_fixos.js monta o payload para POST /api/gastos-fixos
    Então o campo valor do payload é a string "99.90" sem transformação numérica

  # ---------------------------------------------------------------------------
  # Modal editar — .btn-editar-gasto-fixo
  # ---------------------------------------------------------------------------

  Cenário: Clicar em .btn-editar-gasto-fixo preenche o modal com os dados do item
    Dado um item com data-id="7" exibido na seção gastos fixos com os dados: descricao="Spotify", valor="19.90", data="2026-06-15", categoria="GASTOS_FIXOS", forma_pagamento="CARTAO_CREDITO"
    Quando o usuário clica no botão .btn-editar-gasto-fixo desse item
    Então o #modal-gasto-fixo é exibido
    E o campo #gf-id contém "7"
    E o campo #gf-descricao contém "Spotify"
    E o campo #gf-valor contém "19.90"
    E o campo #gf-data contém "2026-06-15"

  Cenário: Salvar edição chama PUT /api/gastos-fixos/{id} com os valores do formulário
    Dado que o #modal-gasto-fixo está aberto em modo editar com #gf-id="7"
    E o campo #gf-descricao contém "Spotify Premium"
    Quando o usuário clica em #btn-salvar-gasto-fixo
    Então é feito um PUT para /api/gastos-fixos/7 com o payload atualizado
    E carregarGastosFixos() é chamado para recarregar a seção

  # ---------------------------------------------------------------------------
  # Remover com confirmação — .btn-remover-gasto-fixo
  # ---------------------------------------------------------------------------

  Cenário: Clicar em .btn-remover-gasto-fixo exibe confirmação antes de deletar
    Dado um item com data-id="5" exibido na seção gastos fixos
    Quando o usuário clica no botão .btn-remover-gasto-fixo do item
    Então uma mensagem de confirmação é exibida ao usuário antes de prosseguir

  Cenário: Confirmar remoção chama DELETE /api/gastos-fixos/{id} e item some da seção
    Dado que o usuário confirmou a remoção do item com data-id="5"
    Quando DELETE /api/gastos-fixos/5 retorna 200 {"ok": true}
    Então o item com data-id="5" é removido do #gastos-fixos-container
    E carregarGastosFixos() é chamado para atualizar a seção

  Cenário: Cancelar confirmação não faz a requisição DELETE
    Dado que o usuário clicou em .btn-remover-gasto-fixo do item data-id="5"
    Quando o usuário cancela a confirmação
    Então nenhuma requisição DELETE é feita para /api/gastos-fixos/5
    E o item permanece na seção

  # ---------------------------------------------------------------------------
  # Exibição de erros do backend em #gf-erro
  # ---------------------------------------------------------------------------

  Cenário: Erro 400 do POST é exibido em #gf-erro
    Dado que o #modal-gasto-fixo está aberto em modo criar
    E o backend retorna 400 {"erro": "Campos obrigatorios ausentes: valor"}
    Quando o usuário clica em #btn-salvar-gasto-fixo
    Então o elemento #gf-erro exibe o texto "Campos obrigatorios ausentes: valor"
    E o #modal-gasto-fixo permanece aberto

  Cenário: Erro 404 do PUT é exibido em #gf-erro no modo editar
    Dado que o #modal-gasto-fixo está aberto em modo editar com #gf-id="99"
    E o backend retorna 404 {"erro": "Gasto fixo nao encontrado"}
    Quando o usuário clica em #btn-salvar-gasto-fixo
    Então o elemento #gf-erro exibe o texto "Gasto fixo nao encontrado"
    E o #modal-gasto-fixo permanece aberto

  Cenário: #gf-erro é limpo ao abrir o modal novamente
    Dado que o #gf-erro exibe uma mensagem de erro anterior
    Quando o usuário clica em #btn-novo-gasto-fixo ou .btn-editar-gasto-fixo
    Então o #gf-erro está vazio

  # ---------------------------------------------------------------------------
  # Recarregar sem reload da página
  # ---------------------------------------------------------------------------

  Cenário: Após salvar com sucesso a seção é atualizada sem reload da página completa
    Dado que POST /api/gastos-fixos retornou 201 com sucesso
    Quando gastos_fixos.js processa a resposta
    Então a função carregarGastosFixos() é invocada
    E window.location.reload() não é chamado
