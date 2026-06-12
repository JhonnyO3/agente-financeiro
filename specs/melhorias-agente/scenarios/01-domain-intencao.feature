# language: pt

Funcionalidade: Modelos de domínio — Intencao, ParametrosPorAcao e ResultadoTool
  Como roteador e tools do agente
  Quero que Intencao seja uma union tipada e ResultadoTool tenha shape estável
  Para que erros de tipo sejam pegos em validação Pydantic, não em runtime

  Cenário: Instanciar Intencao de cadastro simples
    Dado um dicionário com acao "cadastrar" e itens contendo descricao "Claude Code" e valor 472
    Quando crio uma instância de Intencao
    Então a instância é válida e acao é "cadastrar"
    E parametros é do tipo ParamsCadastrar com 1 item

  Cenário: Instanciar Intencao de listagem com período
    Dado um dicionário com acao "listar" e parametros contendo periodo "mes_atual"
    Quando crio uma instância de Intencao
    Então a instância é válida e parametros é do tipo ParamsListar

  Esquema do Cenário: Todas as 10 acoes produzem instancias validas
    Dado o exemplo de Intencao "<exemplo>" com acao "<acao>" da tabela de exemplos do classificador.md
    Quando crio uma instância de Intencao
    Então a validação Pydantic passa sem erro
    E parametros é do tipo esperado para "<acao>"

    Exemplos:
      | exemplo                        | acao         |
      | gastei 472 claude code         | cadastrar    |
      | listar gastos                  | listar       |
      | corrige o valor da zara        | atualizar    |
      | apaga o gasto das flores       | excluir      |
      | vale a pena parcelar           | conversar    |
      | confirmar                      | confirmar    |
      | nao deixa                      | cancelar     |
      | opcao 2                        | selecionar   |
      | foi 350                        | complementar |
      | me conta uma piada             | desconhecida |

  Cenário: Parametros do tipo errado para a acao falham validacao
    Dado um dicionário com acao "listar" e parametros do tipo ParamsCadastrar (itens=[...])
    Quando tento criar uma instância de Intencao
    Então o Pydantic levanta ValidationError

  Cenário: Valor monetario em ItemCadastro e armazenado como Decimal
    Dado um ItemCadastro com valor 472 como float
    Quando crio uma instância de ItemCadastro
    Então o campo valor é do tipo Decimal

  Cenário: ResultadoTool aceita todos os pares acao-status definidos no contrato
    Dado os pares validos do contrato resultado-tools
    Quando instancio ResultadoTool para cada par com dados compatíveis
    Então todas as instâncias passam na validação Pydantic

  Cenário: ParamsSelecionar exige opcao inteiro positivo
    Dado um dicionário com acao "selecionar" e parametros contendo opcao 2
    Quando crio uma instância de Intencao
    Então a instância é válida e parametros.opcao é 2
