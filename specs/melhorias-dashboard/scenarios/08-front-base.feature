# language: pt
# Tarefa: T08 — pytest (render) + manual (browser)
Funcionalidade: Front base v2

  Cenário: Novos ids no HTML (pytest)
    Quando faço GET /
    Então o HTML contém card-receitas, projecao-container, filtro-status,
      edit-status, edit-forma-pagamento, edit-responsavel, edit-detalhes,
      add-status, add-forma-pagamento, add-responsavel, add-detalhes
    E os theads têm as colunas Status e Responsável
    E filtro-tipo contém a opção RECEITA

  Cenário: Projeção renderizada (manual)
    Dado parcelas pendentes futuras no banco
    Quando abro a página
    Então a seção de projeção mostra 6 meses com somas e cor por sinal

  Cenário: Card de receitas (manual)
    Então o card Receitas mostra o total e o Saldo reflete receitas − gastos
