# language: pt
# Tarefa: T04 — testes automatizados (pytest, repository mockado)
Funcionalidade: API de parcelas ativas e exclusão de grupo

  Cenário: Lista apenas grupos parcelados com parcela futura
    Dado um grupo com parcelas 3..12 futuras (total 12) e uma transação à vista futura
    Quando faço GET /api/parcelas-ativas
    Então recebo apenas o grupo parcelado
    E o item tem parcela_numero 3, parcela_total 12, pagas 2 e proxima_data da parcela 3

  Cenário: Ordenação por próxima data
    Dado dois grupos com próximas datas diferentes
    Quando faço GET /api/parcelas-ativas
    Então o grupo com data mais próxima vem primeiro

  Cenário: Excluir grupo existente
    Dado um grupo com 12 parcelas
    Quando faço DELETE /api/grupos/<uuid-do-grupo>
    Então recebo 200 com {"ok": true, "removidos": 12}

  Cenário: Excluir grupo inexistente
    Quando faço DELETE /api/grupos/<uuid-aleatorio>
    Então recebo 404

  Cenário: UUID inválido
    Quando faço DELETE /api/grupos/nao-e-uuid
    Então recebo 400
