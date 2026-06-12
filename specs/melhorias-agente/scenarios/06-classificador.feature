# language: pt

Funcionalidade: Classificador — LLM retorna Intencao tipada para as 10 intencoes
  Como roteador
  Quero que o classificador converta a mensagem do usuario em Intencao validada
  Para rotear deterministicamente sem interpretar dict livre

  Esquema do Cenário: Classificador produz acao correta para exemplos do classificador.md
    Dado um mock de LLM configurado para devolver acao "<acao>" com confianca <confianca>
    E estado_pendente "<estado_pendente>"
    Quando chamo classificador.classificar("<mensagem>", historico=[], estado_pendente="<estado_pendente>")
    Então a Intencao retornada tem acao "<acao>"

    Exemplos:
      | mensagem                                      | estado_pendente                   | acao         | confianca |
      | Gastei 472 reais com Claude code              | nenhuma                           | cadastrar    | 0.98      |
      | 140 das flores e 190 de internet ontem        | nenhuma                           | cadastrar    | 0.96      |
      | listar gastos                                 | nenhuma                           | listar       | 0.99      |
      | quanto gastei esse mês?                       | nenhuma                           | listar       | 0.97      |
      | estou no azul esse mês?                       | nenhuma                           | listar       | 0.92      |
      | vale a pena parcelar uma compra grande?       | nenhuma                           | conversar    | 0.93      |
      | corrige o valor da zara para 200              | nenhuma                           | atualizar    | 0.96      |
      | paguei a internet                             | nenhuma                           | atualizar    | 0.94      |
      | apaga o gasto das flores                      | nenhuma                           | excluir      | 0.95      |
      | apaga tudo de maio                            | nenhuma                           | excluir      | 0.95      |
      | confirmar                                     | cadastro aguardando confirmação   | confirmar    | 0.99      |
      | não, deixa                                    | exclusão aguardando confirmação   | cancelar     | 0.98      |
      | 2                                             | lista de 3 opções exibida         | selecionar   | 0.99      |
      | todos                                         | exclusão aguardando escopo        | selecionar   | 0.97      |
      | foi 350                                       | cadastro aguardando valor         | complementar | 0.97      |
      | em 3x                                         | cadastro aguardando parcelas      | complementar | 0.97      |
      | me conta uma piada                            | nenhuma                           | desconhecida | 0.99      |

  Cenário: confianca abaixo de CONFIANCA_MINIMA retorna acao desconhecida
    Dado um mock de LLM que devolve acao "cadastrar" com confianca 0.5
    E Settings.CONFIANCA_MINIMA = 0.7
    Quando chamo classificar("mensagem ambigua", historico=[], estado_pendente="nenhuma")
    Então a Intencao retornada tem acao "desconhecida"

  Cenário: classificador injeta historico e estado_pendente no prompt
    Dado um mock de LLM que captura o prompt recebido
    E um histórico com 2 mensagens e estado_pendente "cadastro aguardando confirmação"
    Quando chamo classificar("confirmar", historico=[...], estado_pendente="cadastro aguardando confirmação")
    Então o prompt enviado ao LLM contém o histórico formatado
    E o prompt contém "cadastro aguardando confirmação"

  Cenário: intenção nova durante pendência não força confirmar
    Dado um mock de LLM que devolve acao "cadastrar" para "gastei 30 no uber" com confianca 0.95
    E estado_pendente "exclusão aguardando confirmação"
    Quando chamo classificar("gastei 30 no uber", historico=[], estado_pendente="exclusão aguardando confirmação")
    Então a Intencao retornada tem acao "cadastrar"
    E parametros contém descricao "Uber" e valor 30

  Cenário: estado_pendente nenhuma nunca produz confirmar cancelar selecionar complementar
    Dado um mock de LLM que tentaria devolver acao "confirmar" com confianca 0.8
    E estado_pendente "nenhuma"
    Quando chamo classificar("sim", historico=[], estado_pendente="nenhuma")
    Então a Intencao retornada NÃO tem acao "confirmar"
