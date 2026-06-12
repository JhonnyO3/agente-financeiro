# language: pt

Funcionalidade: Tool Listar — agregacao deterministica sem LLM
  Como usuario
  Quero ver meus gastos agrupados por categoria com subtotais e split pago/pendente
  Para entender minha situação financeira sem ambiguidade

  Cenário: listar mes atual sem filtros retorna registros agrupados por categoria
    Dado um repository mockado com 3 transações em Jun/2026: Internet (GASTOS_FIXOS, PAGO), Flores (COMPRAS, PAGO), Academia (GASTOS_FIXOS, PAGO)
    E Relogio mockado retornando mês atual = "2026-06"
    Quando chamo ToolListar.executar(params_vazios, contexto)
    Então ResultadoTool.status é "concluido"
    E dados.grupos contém grupo "GASTOS_FIXOS" com 2 itens e subtotal Decimal("310.00")
    E dados.grupos contém grupo "COMPRAS" com 1 item
    E dados.periodo_label é "Jun/2026"

  Cenário: registros parcelados entram na secao PARCELAMENTOS nao na categoria
    Dado um repository mockado com 1 transação parcelada Batman PS5 parcela_total=4 (LAZER)
    Quando chamo ToolListar.executar(params_vazios, contexto)
    Então dados.grupos contém grupo "PARCELAMENTOS"
    E o item Batman PS5 está em PARCELAMENTOS
    E o item Batman PS5 NÃO está em "LAZER"

  Cenário: split pago-pendente em Decimal sem usar LLM
    Dado um repository mockado com Internet R$190 PAGO e Batman PS5 R$200 PENDENTE
    Quando chamo ToolListar.executar(params_vazios, contexto)
    Então dados.pago é Decimal("190.00")
    E dados.pendente é Decimal("200.00")
    E dados.total é Decimal("390.00")
    E nenhuma chamada LLM foi feita

  Cenário: periodo ausente usa mes atual via Relogio
    Dado params com periodo=None
    E Relogio mockado retornando hoje = date(2026, 6, 11)
    Quando chamo ToolListar.executar(params, contexto)
    Então o repository foi consultado com período "2026-06"

  Cenário: periodo com nome de mes e convertido corretamente
    Dado params com periodo="maio"
    Quando chamo ToolListar.executar(params, contexto)
    Então o repository foi consultado com período "2026-05"

  Cenário: nenhum registro no periodo retorna status vazio
    Dado um repository mockado sem transações em Jan/2026
    E params com periodo="2026-01"
    Quando chamo ToolListar.executar(params, contexto)
    Então ResultadoTool.status é "vazio"

  Cenário: filtro de categoria reduz a listagem
    Dado um repository mockado com transações de GASTOS_FIXOS e COMPRAS
    E params com categoria="COMPRAS"
    Quando chamo ToolListar.executar(params, contexto)
    Então dados.grupos contém apenas o grupo "COMPRAS"
    E GASTOS_FIXOS não aparece
