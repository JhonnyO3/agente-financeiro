# language: pt

Funcionalidade: Tool Cadastrar — monta registros sem persistir
  Como roteador
  Quero que ToolCadastrar monte os registros com as regras de negócio
  E devolva status aguardando_confirmacao ou aguardando_complemento sem tocar o banco

  Cenário: PIX simples gera 1 registro PAGO hoje aguardando confirmacao
    Dado um item com descricao "Claude Code", valor 472, forma_pagamento None (não informada)
    E Relogio mockado retornando hoje = date(2026, 6, 11)
    Quando chamo ToolCadastrar.executar([item], contexto)
    Então ResultadoTool.status é "aguardando_confirmacao"
    E dados.registros tem 1 elemento
    E o registro tem forma_pagamento "PIX" e status "PAGO"
    E o registro tem data date(2026, 6, 11)
    E o registro tem responsavel == Settings.RESPONSAVEL_PADRAO

  Cenário: cartao parcelado 3/5 com vencimento dia 10 gera 3 registros (atual+futuras)
    Dado um item com descricao "Roupas Zara", forma_pagamento "CARTAO_CREDITO", parcela_atual=3, total_parcelas=5, dia_vencimento=10
    E Relogio mockado retornando hoje = date(2026, 6, 11)
    Quando chamo ToolCadastrar.executar([item], contexto)
    Então ResultadoTool.status é "aguardando_confirmacao"
    E dados.registros tem 3 elementos (parcelas 3, 4, 5)
    E todos os registros têm o mesmo grupo_parcela_id
    E os registros têm datas 10/06/2026, 10/07/2026, 10/08/2026
    E dados.parcelas_futuras é ["Jul/26", "Ago/26"]

  Cenário: status da parcela atual por data de vencimento futura resulta em PENDENTE
    Dado um item parcelado com dia_vencimento=10 e Relogio.hoje() = date(2026, 6, 11) (vencimento futuro)
    Quando chamo ToolCadastrar.executar([item], contexto)
    Então o registro da parcela atual tem status "PENDENTE"

  Cenário: status da parcela atual com vencimento hoje ou passado resulta em PAGO
    Dado um item parcelado com dia_vencimento=5 e Relogio.hoje() = date(2026, 6, 11) (vencimento passado)
    Quando chamo ToolCadastrar.executar([item], contexto)
    Então o registro da parcela atual tem status "PAGO"

  Cenário: valor ausente retorna aguardando_complemento com campos_faltantes valor
    Dado um item com descricao "Zara" e valor None
    Quando chamo ToolCadastrar.executar([item], contexto)
    Então ResultadoTool.status é "aguardando_complemento"
    E dados.campos_faltantes contém "valor"

  Cenário: multiplos gastos na mesma mensagem geram lista de registros
    Dado dois itens: "Flores Natasha" R$140 e "Internet" R$190 data="ontem"
    E Relogio mockado retornando hoje = date(2026, 6, 11)
    Quando chamo ToolCadastrar.executar([item1, item2], contexto)
    Então ResultadoTool.status é "aguardando_confirmacao"
    E dados.registros tem 2 elementos com valores Decimal(140) e Decimal(190)

  Cenário: DINHEIRO como forma de pagamento e mapeado para PIX com detalhes
    Dado um item com forma_pagamento "DINHEIRO"
    Quando chamo ToolCadastrar.executar([item], contexto)
    Então o registro tem forma_pagamento "PIX"
    E o registro tem detalhes "dinheiro"

  Cenário: responsavel sempre preenchido com RESPONSAVEL_PADRAO nunca usa default do DTO
    Dado Settings.RESPONSAVEL_PADRAO = "Jhonatas"
    E um item sem campo responsavel
    Quando chamo ToolCadastrar.executar([item], contexto)
    Então o registro tem responsavel "Jhonatas"

  Cenário: matematica de parcelas em Decimal sem arredondamento float
    Dado um item com valor 100 e total_parcelas=3
    Quando chamo ToolCadastrar.executar([item], contexto)
    Então os valores das parcelas são Decimal("33.33"), Decimal("33.33"), Decimal("33.34")
    E a soma dos valores equals Decimal("100.00")
