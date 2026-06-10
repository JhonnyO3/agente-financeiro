# language: pt
# Tarefa: T07 — pytest (repository mockado)
Funcionalidade: API transações v2

  Cenário: Serialização com os novos campos
    Quando faço GET /api/transacoes
    Então cada item tem status, forma_pagamento, responsavel e detalhes ("" se null)

  Cenário: Filtro por status combinado
    Quando faço GET /api/transacoes?status=PENDENTE&tipo=GASTO
    Então só voltam gastos pendentes

  Cenário: POST com defaults e validação
    Quando faço POST sem os campos novos
    Então o TransacaoCreate usa PENDENTE/OUTRO/"Jhonatas"/None
    E POST com status="XYZ" retorna 400

  Cenário: POST via PIX nasce pago
    Quando faço POST com forma_pagamento=PIX
    Então o TransacaoCreate tem status=PAGO

  Cenário: PUT parcial de status
    Quando faço PUT com {"status": "PAGO"}
    Então TransacaoUpdate tem apenas status preenchido
