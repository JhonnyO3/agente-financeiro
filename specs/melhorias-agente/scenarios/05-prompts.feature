# language: pt

Funcionalidade: Sistema de prompts base + injection e funcao montar_prompt
  Como classificador e tools com LLM
  Quero que montar_prompt monte o prompt completo substituindo todas as variáveis
  Para que cada chamada LLM receba apenas sua injection sem contaminação entre ações

  Cenário: montar_prompt para classificador injeta o arquivo correto e preenche todas as variaveis
    Dado um contexto com user_name, data_atual, responsavel_padrao, historico_recente, estado_pendente
    Quando chamo montar_prompt("classificador", contexto)
    Então o resultado contém o conteúdo de 01-classificador.md expandido
    E não há placeholders {variavel} não substituídos no texto de saída

  Cenário: montar_prompt para cadastrar injeta 02-extracao-cadastrar.md
    Dado um contexto completo incluindo a variavel "parametros"
    Quando chamo montar_prompt("cadastrar", contexto)
    Então o resultado contém o conteúdo de 02-extracao-cadastrar.md
    E não há placeholders não substituídos

  Cenário: montar_prompt para atualizar injeta 03-extracao-atualizar.md
    Dado um contexto completo incluindo "parametros" e "candidatos"
    Quando chamo montar_prompt("atualizar", contexto)
    Então o resultado contém o conteúdo de 03-extracao-atualizar.md
    E não há placeholders não substituídos

  Cenário: montar_prompt para conversar injeta 06-conversar.md
    Dado um contexto completo incluindo a variavel "mensagem"
    Quando chamo montar_prompt("conversar", contexto)
    Então o resultado contém o conteúdo de 06-conversar.md
    E o prompt não contém referência a contexto_rag nem acesso ao banco

  Cenário: responsavel_padrao resolve de Settings nunca de string fixa
    Dado Settings com RESPONSAVEL_PADRAO="Teste"
    E um contexto sem a chave responsavel_padrao fornecida explicitamente
    Quando montar_prompt injeta o base automaticamente com responsavel_padrao de Settings
    Então o texto contém "Teste" como responsavel_padrao

  Cenário: variavel obrigatoria ausente no contexto falha explicitamente
    Dado um contexto faltando a variável "historico_recente"
    Quando chamo montar_prompt("classificador", contexto)
    Então uma exceção é levantada (KeyError ou ValueError)
    E não produz prompt com placeholder não substituído silenciosamente

  Cenário: nao existem prompts para listar ou excluir
    Dado o dicionário ARQUIVO_POR_ACAO de prompts.py
    Quando verifico as chaves presentes
    Então as chaves são exatamente "classificador", "cadastrar", "atualizar", "conversar"
    E "listar" e "excluir" não estão presentes
