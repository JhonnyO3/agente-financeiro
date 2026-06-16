# language: pt
Funcionalidade: Wiring multi-usuário e histórico configurável
  RN-14, RN-15. repo_factory por mensagem; sem usuario_id fixo.

  Cenário: App sobe sem WHATSAPP_ALLOWED_NUMBER
    Dado um ambiente sem WHATSAPP_ALLOWED_NUMBER definido
    Quando o app é importado e o lifespan inicia
    Então o app sobe sem erro

  Cenário: repo_factory produz repositório escopado por usuario_id
    Dado o app inicializado
    Quando chamo app.state.repo_factory(7)
    Então recebo um repositório com usuario_id igual a 7

  Cenário: Consumidor desempacota a tupla de 3 elementos
    Dado um item de fila (42, "5511999998888", "gastei 50")
    Quando o consumidor o processa
    Então worker.receber é chamado com (42, "5511999998888", "gastei 50")

  Cenário: Histórico respeita o máximo configurável
    Dado HISTORICO_MAX_MENSAGENS igual a 10
    Quando 12 mensagens são registradas
    Então apenas as últimas 10 permanecem no histórico

  Cenário: Histórico expira por inatividade
    Dado HISTORICO_TTL_HORAS igual a 2
    E um histórico cuja expiração já passou
    Quando o estado é obtido
    Então o histórico volta vazio

  Cenário: Nenhuma referência a WHATSAPP_ALLOWED_NUMBER no código
    Então config e wiring não declaram WHATSAPP_ALLOWED_NUMBER
