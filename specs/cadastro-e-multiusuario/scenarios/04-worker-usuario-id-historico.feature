# language: pt
Funcionalidade: Worker multi-usuário com histórico e isolamento
  RN-12, RN-13, RN-14, RN-17. Histórico carregado antes de classificar.

  Cenário: Histórico é carregado antes de classificar
    Dado um usuário com 3 mensagens prévias no histórico
    Quando o worker processa uma nova mensagem desse usuário
    Então o estado é obtido antes da chamada ao classificador
    E o classificador recebe o histórico com as 3 mensagens prévias

  Cenário: Mensagem do usuário é registrada com usuario_id e instante
    Quando o worker processa a mensagem do usuário 7
    Então registrar_mensagem é chamado com usuario_id 7 e o instante atual

  Cenário: Dois usuários são processados isoladamente
    Dado o usuário A (id 1) e o usuário B (id 2)
    Quando ambos enviam a mesma mensagem
    Então o roteador do usuário A usa o repositório escopado em id 1
    E o roteador do usuário B usa o repositório escopado em id 2
    E nenhum repositório é compartilhado entre eles

  Cenário: Histórico de um usuário não vaza para o outro
    Dado histórico existente para o usuário A
    Quando o usuário B é processado
    Então o classificador do usuário B recebe apenas o histórico do usuário B

  Cenário: Falha no pipeline envia mensagem amigável sem derrubar o worker
    Dado que o classificador lança exceção
    Quando o worker processa a mensagem
    Então uma mensagem amigável é enviada ao número de origem
    E o worker continua operante
