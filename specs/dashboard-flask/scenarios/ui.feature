# language: pt
# Tarefas: T06-T09 — verificação: T06 via pytest (render), T07-T09 manual no browser
Funcionalidade: Interface do dashboard

  Cenário: Página principal renderiza com todos os containers (T06)
    Quando faço GET /
    Então recebo 200
    E o HTML contém os ids: card-gastos, card-investimentos, card-saldo,
      chart-pizza, chart-barras, chart-linha, parcelas-container,
      tabela-transacoes, paginacao, filtro-tipo, filtro-categoria,
      tabela-investimentos, card-invest-periodo, card-invest-total,
      modal-editar, modal-adicionar

  Cenário: Seletor de período (T06)
    Quando faço GET /?periodo=ano_atual
    Então o select de período tem 6 opções e "ano_atual" está selecionado

  Cenário: Gráficos renderizam e pizza filtra tabela (T07, manual)
    Dado dados no banco
    Quando abro a página e clico numa fatia da pizza
    Então a tabela de transações filtra pela categoria clicada

  Cenário: CRUD pela tabela sem reload (T08, manual)
    Quando edito, adiciono e excluo transações pelos modais
    Então a tabela re-renderiza sem recarregar a página e o banco reflete as mudanças

  Cenário: Cards e parcelas (T09, manual)
    Quando abro a página com dados
    Então os cards mostram valores em BRL, saldo colorido pelo sinal
    E os cards de parcela mostram barra de progresso e botão de excluir grupo com confirmação
