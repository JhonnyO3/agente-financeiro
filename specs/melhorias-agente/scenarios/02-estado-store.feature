# language: pt

Funcionalidade: EstadoConversa, EstadoStore e resumo de pendência
  Como worker e roteador
  Quero que o estado conversacional persista (Redis em produção, memória nos testes) com TTLs independentes
  Para que pendências e histórico expirem isoladamente sem perda cruzada

  # Os cenários abaixo valem para AMBAS as implementações (EstadoStoreRedis com
  # cliente AsyncMock e EstadoStoreMemoria) — mesma suíte de comportamento.

  Cenário: obter estado para usuario inexistente devolve estado limpo
    Dado que o EstadoStore está vazio
    Quando chamo obter(usuario_id=1, agora=<now>)
    Então recebo um EstadoConversa com usuario_id=1 e todos os campos None/vazios
    E o retorno não é None

  Cenário: EstadoStoreRedis serializa e desserializa via JSON com TTL fisico
    Dado um EstadoStoreRedis com cliente Redis mockado (AsyncMock)
    E um EstadoConversa com usuario_id=1 e acao_pendente "cadastrar"
    Quando chamo salvar(estado)
    Então o cliente recebeu set/setex na chave "estado:1" com o JSON do estado e TTL de 24h
    E quando obter(usuario_id=1) com o mock devolvendo esse JSON, o estado é reconstruído fielmente

  Cenário: salvar e recuperar estado ativo
    Dado um EstadoConversa com usuario_id=1 e acao_pendente "cadastrar" e payload_pendente {"x": 1}
    Quando salvo e depois chamo obter(usuario_id=1, agora=<agora_valido>)
    Então o estado devolvido contém acao_pendente "cadastrar" e payload_pendente {"x": 1}

  Cenário: pendencia expira apos 5 minutos sem afetar historico
    Dado um EstadoConversa com usuario_id=1, acao_pendente "excluir" e expira_em = agora - 1 segundo
    E o histórico contém 2 mensagens com historico_expira_em ainda válido
    Quando chamo obter(usuario_id=1, agora=<agora_apos_expiracao>)
    Então acao_pendente é None e payload_pendente é None
    E historico ainda contém as 2 mensagens

  Cenário: historico expira apos 24 horas sem afetar pendencia ativa
    Dado um EstadoConversa com usuario_id=1 com historico_expira_em = agora - 1 segundo
    E acao_pendente "atualizar" com expira_em ainda válido
    Quando chamo obter(usuario_id=1, agora=<agora_apos_expiracao_historico>)
    Então historico está vazio
    E acao_pendente ainda é "atualizar"

  Cenário: limpar_pendencia preserva historico
    Dado um EstadoConversa com usuario_id=1 com acao_pendente "cadastrar" e 3 mensagens no historico
    Quando chamo limpar_pendencia(usuario_id=1)
    Então acao_pendente é None, payload_pendente é None, opcoes é None, campos_faltantes é []
    E historico contém as 3 mensagens originais

  Cenário: registrar_mensagem mantém anel de no maximo 5 mensagens
    Dado um EstadoConversa com usuario_id=1 e 5 mensagens já no historico
    Quando chamo registrar_mensagem com uma nova mensagem de papel "usuario"
    Então historico contém exatamente 5 mensagens
    E a mensagem mais antiga foi descartada
    E a nova mensagem está na posição final

  Cenário: resumir_pendencia retorna "nenhuma" quando nao ha pendencia
    Dado um EstadoConversa sem acao_pendente
    Quando chamo resumir_pendencia(estado)
    Então retorna a string "nenhuma"

  Esquema do Cenário: resumir_pendencia cobre os formatos do classificador.md
    Dado um EstadoConversa com acao_pendente "<acao>" e campos "<detalhe>"
    Quando chamo resumir_pendencia(estado)
    Então o resultado contém "<fragmento_esperado>"

    Exemplos:
      | acao      | detalhe                             | fragmento_esperado                  |
      | cadastrar | payload_pendente pronto             | cadastro aguardando confirmação     |
      | cadastrar | campos_faltantes=["valor"]          | cadastro aguardando valor           |
      | atualizar | opcoes com 3 itens                  | lista de 3 opções exibida           |
      | excluir   | opcoes escopo (somente este, todos) | exclusão aguardando escopo          |
