# language: pt

Funcionalidade: Tool Conversar — dialogo financeiro puro sem acesso ao banco
  Como usuario
  Quero respostas em linguagem natural sobre conceitos financeiros
  Sem que o agente consulte o banco de dados

  Cenário: conversar retorna resposta em linguagem natural
    Dado um LLM mockado configurado para retornar "Vale sim, depende do CET"
    E mensagem "vale a pena parcelar uma compra grande?"
    Quando chamo ToolConversar.executar(mensagem, historico=[])
    Então ResultadoTool.acao é "conversar"
    E ResultadoTool.status é "concluido"
    E dados.resposta é "Vale sim, depende do CET"

  Cenário: repository nunca e chamado durante conversar
    Dado um repository mockado que registraria qualquer chamada
    E um LLM mockado retornando resposta qualquer
    Quando chamo ToolConversar.executar(mensagem, historico=[])
    Então o repository não recebeu nenhuma chamada

  Cenário: conversar inclui historico no prompt do LLM
    Dado um LLM mockado que captura o prompt recebido
    E historico com 2 mensagens anteriores
    Quando chamo ToolConversar.executar("como economizar?", historico=[msg1, msg2])
    Então o prompt enviado ao LLM contém as 2 mensagens do histórico

  Cenário: conversar usa o modelo LLM_MODELO_CONVERSAR de Settings
    Dado Settings.LLM_MODELO_CONVERSAR = "gpt-4o"
    E um spy no criar_llm
    Quando chamo ToolConversar.executar(mensagem, historico=[])
    Então criar_llm foi chamado com o modelo "gpt-4o"

  Cenário: prompt de conversar nao contem contexto_rag nem instrucao de banco
    Dado um spy no montar_prompt
    Quando chamo ToolConversar.executar("me dá uma dica", historico=[])
    Então montar_prompt foi chamado com acao="conversar"
    E o contexto não contém "contexto_rag"
