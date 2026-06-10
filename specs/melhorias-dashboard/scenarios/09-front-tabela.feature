# language: pt
# Tarefa: T09 — node --check + manual (browser)
Funcionalidade: Tabela v2

  Cenário: Badges de status (manual)
    Quando a tabela carrega
    Então PAGO aparece com badge verde e PENDENTE com badge amarelo nas duas tabelas

  Cenário: Filtro de status (manual)
    Quando seleciono PENDENTE no filtro-status com tipo=GASTO
    Então a query string contém ambos e a tabela volta à página 1

  Cenário: Modais com os novos campos (manual)
    Quando edito uma transação
    Então o modal pré-preenche status/forma/responsável/detalhes e o PUT os envia
    E o modal adicionar envia os campos no POST

  Cenário: Tooltip de detalhes (manual)
    Dado item com detalhes não vazio
    Então a célula Descrição tem title com o texto
