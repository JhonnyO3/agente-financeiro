# language: pt

Funcionalidade: Tools Atualizar e Excluir — RAG 3 faixas, diff, propagacao e escopo de parcelas
  Como roteador
  Quero que Atualizar e Excluir usem RAG para localizar registros e nunca persistam diretamente
  Para que o usuario sempre confirme antes da escrita

  # ---- ATUALIZAR ----

  Cenário: Atualizar com RAG MATCH gera diff aguardando confirmacao
    Dado BuscaRAG mockado retornando MATCH com transacao Internet (status=PENDENTE)
    E params atualizar com referencia="internet", campo="status", novo_valor="PAGO"
    Quando chamo ToolAtualizar.executar(params, contexto)
    Então ResultadoTool.status é "aguardando_confirmacao"
    E dados.diff contém campo "status", antigo "PENDENTE", novo "PAGO"
    E o registro não foi alterado no banco

  Cenário: Atualizar com RAG AMBIGUO gera aguardando_selecao com lista de opcoes
    Dado BuscaRAG mockado retornando AMBIGUO com [Roupas Zara, Batman PS5]
    E params atualizar com referencia="cartao"
    Quando chamo ToolAtualizar.executar(params, contexto)
    Então ResultadoTool.status é "aguardando_selecao"
    E dados.opcoes tem 2 itens numerados

  Cenário: Atualizar com RAG PISO retorna nao_encontrado
    Dado BuscaRAG mockado retornando PISO
    E params atualizar com referencia="inexistente"
    Quando chamo ToolAtualizar.executar(params, contexto)
    Então ResultadoTool.status é "nao_encontrado"
    E dados.referencia é "inexistente"

  Cenário: Atualizar campo valor com parcelas futuras propaga e lista afetadas
    Dado BuscaRAG mockado retornando MATCH com transacao Roupas Zara parcela 3/5 grupo_id=G1
    E repository mockado com parcelas futuras do grupo G1: Jul/26, Ago/26
    E params atualizar com referencia="zara", campo="valor", novo_valor="200"
    Quando chamo ToolAtualizar.executar(params, contexto)
    Então ResultadoTool.status é "aguardando_confirmacao"
    E dados.parcelas_afetadas é ["Jul/26", "Ago/26"]

  Cenário: Atualizar campo data com parcelas futuras propaga
    Dado BuscaRAG mockado retornando MATCH com transacao parcelada grupo G1
    E params atualizar com campo="data", novo_valor="15/07/2026"
    Quando chamo ToolAtualizar.executar(params, contexto)
    Então dados.parcelas_afetadas é nao vazio

  Cenário: Atualizar campo status nao propaga para parcelas futuras
    Dado BuscaRAG mockado retornando MATCH com transacao parcelada grupo G1
    E params atualizar com campo="status", novo_valor="PAGO"
    Quando chamo ToolAtualizar.executar(params, contexto)
    Então dados.parcelas_afetadas é [] (vazio)

  # ---- EXCLUIR ----

  Cenário: Excluir individual simples sem parcelas gera aguardando_confirmacao
    Dado BuscaRAG mockado retornando MATCH com transacao Flores Natasha (parcela_total=1)
    E params excluir com referencia="flores"
    Quando chamo ToolExcluir.executar(params, contexto)
    Então ResultadoTool.status é "aguardando_confirmacao"
    E dados.registro contém descricao "Flores Natasha"
    E o banco não foi modificado

  Cenário: Excluir registro parcelado retorna aguardando_escopo com opcoes numeradas
    Dado BuscaRAG mockado retornando MATCH com transacao Batman PS5 parcela 2/4 com parcelas futuras Jul/26 Ago/26 Set/26
    E params excluir com referencia="batman"
    Quando chamo ToolExcluir.executar(params, contexto)
    Então ResultadoTool.status é "aguardando_escopo"
    E dados.parcelas_futuras é ["Jul/26", "Ago/26", "Set/26"]

  Cenário: Excluir em modo lote por periodo gera count e aguardando_confirmacao
    Dado um repository mockado com 5 transações em maio/2026
    E params excluir com periodo="2026-05" e referencia=None
    Quando chamo ToolExcluir.executar(params, contexto)
    Então ResultadoTool.status é "aguardando_confirmacao"
    E dados.modo é "lote"
    E dados.qtd é 5
    E dados.periodo_label é "Mai/2026"

  Cenário: Excluir com RAG AMBIGUO retorna aguardando_selecao
    Dado BuscaRAG mockado retornando AMBIGUO com [Internet Jun, Internet Mai]
    E params excluir com referencia="internet"
    Quando chamo ToolExcluir.executar(params, contexto)
    Então ResultadoTool.status é "aguardando_selecao"
    E dados.modo é "individual"

  Cenário: Excluir com RAG PISO retorna nao_encontrado
    Dado BuscaRAG mockado retornando PISO
    E params excluir com referencia="inexistente"
    Quando chamo ToolExcluir.executar(params, contexto)
    Então ResultadoTool.status é "nao_encontrado"
