# language: pt

Funcionalidade: Roteador — match de intencao, guarda de pendencia e confirmar sem LLM
  Como worker
  Quero que o Roteador direcione cada Intencao para a Tool correta
  E que confirmacoes persistam o payload_pendente ja montado sem nova chamada LLM

  Cenário: intencao cadastrar direciona para ToolCadastrar
    Dado uma Intencao com acao="cadastrar" e params validos
    E estado sem pendencia
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então ToolCadastrar.executar foi chamado
    E o resultado é o retorno de ToolCadastrar

  Cenário: intencao listar direciona para ToolListar sem LLM
    Dado uma Intencao com acao="listar"
    E estado sem pendencia
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então ToolListar.executar foi chamado
    E nenhuma chamada LLM foi feita

  Cenário: intencao confirmar com pendencia de cadastrar persiste sem LLM
    Dado uma Intencao com acao="confirmar"
    E estado com acao_pendente="cadastrar" e payload_pendente={"registros": [...]}
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então o repository.criar_lote foi chamado com o payload_pendente
    E nenhuma chamada LLM foi feita
    E o estado teve limpar_pendencia chamado apos persistir

  Cenário: intencao confirmar com pendencia de atualizar persiste sem LLM
    Dado uma Intencao com acao="confirmar"
    E estado com acao_pendente="atualizar" e payload_pendente com diff
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então o repository.atualizar foi chamado
    E nenhuma chamada LLM foi feita

  Cenário: intencao cancelar com pendencia limpa o estado e retorna menu
    Dado uma Intencao com acao="cancelar"
    E estado com acao_pendente="excluir"
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então limpar_pendencia foi chamado
    E o resultado tem acao="menu"

  Cenário: intencao nova durante pendencia ativa cancela a pendencia e processa a nova
    Dado uma Intencao com acao="cadastrar" (nova operação)
    E estado com acao_pendente="excluir" ativo (pendencia nao expirada)
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então limpar_pendencia foi chamado antes de rotear
    E ToolCadastrar.executar foi chamado com a nova intencao
    E a pendencia anterior foi descartada

  Cenário: confirmar sem estado ativo retorna menu
    Dado uma Intencao com acao="confirmar"
    E estado sem pendencia (acao_pendente=None)
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então o resultado tem acao="menu" e status="concluido"
    E nenhuma tool ou repository foi chamado

  Cenário: selecionar sem estado ativo retorna menu
    Dado uma Intencao com acao="selecionar"
    E estado sem pendencia
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então o resultado tem acao="menu"

  Cenário: complementar sem estado ativo retorna menu
    Dado uma Intencao com acao="complementar"
    E estado sem pendencia
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então o resultado tem acao="menu"

  Cenário: tool com status aguardando_confirmacao tem payload guardado no estado
    Dado ToolCadastrar mockada retornando status="aguardando_confirmacao" e dados={"registros": [...]}
    E uma Intencao com acao="cadastrar"
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então EstadoStore.salvar foi chamado com acao_pendente="cadastrar" e payload_pendente preenchido
    E expira_em foi setado em ~5 minutos a partir de agora

  Cenário: selecionar resolve opcao do estado e completa o fluxo
    Dado uma Intencao com acao="selecionar" e parametros.opcao=2
    E estado com acao_pendente="excluir" e opcoes=[opcao1, opcao2]
    Quando chamo Roteador.rotear(intencao, estado, contexto)
    Então a opcao 2 foi resolvida e o fluxo de excluir segue com o registro correspondente
