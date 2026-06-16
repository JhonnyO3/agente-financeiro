# language: pt
Funcionalidade: ToolListar usa o parser de período
  ToolListar delega a resolução de período a parsear_periodo, sem lógica duplicada.

  Cenário: listar do dia corrente quando período é hoje
    Dado um relógio fixado em 15/06/2026
    E transações cadastradas em 15/06 e em 10/06
    Quando executo ToolListar com periodo="hoje"
    Então o repositório é consultado com início e fim em 15/06/2026
    E o label do período é "hoje"

  Cenário: listar do mês quando período é None
    Dado um relógio fixado em 15/06/2026
    Quando executo ToolListar com periodo=None
    Então o repositório é consultado de 01/06/2026 a 30/06/2026
    E o label do período é "Jun/2026"

  Cenário: nenhum código de resolução duplicado em listar.py
    Dado o módulo agent/tools/listar.py
    Quando inspeciono o arquivo
    Então não existe a função _resolver_periodo
    E a resolução vem de agent.services.parser_periodo.parsear_periodo

  Cenário: comportamento de filtros e totais inalterado
    Dado transações de Jun/2026 com categorias, status e parcelados
    Quando executo ToolListar com periodo="mes_atual"
    Então grupos, subtotais, total, pendente e pago são idênticos ao comportamento anterior
