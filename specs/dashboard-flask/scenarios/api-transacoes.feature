# language: pt
# Tarefa: T05 — testes automatizados (pytest, repository mockado)
Funcionalidade: API CRUD de transações

  Cenário: Listagem paginada com 25 por página
    Dado 38 transações no período
    Quando faço GET /api/transacoes?pagina=1
    Então recebo 25 itens, total 38, paginas 2, por_pagina 25
    E ordenados por data DESC, id DESC

  Cenário: Filtros combinados tipo e categoria
    Dado transações de tipos e categorias variados
    Quando faço GET /api/transacoes?tipo=GASTO&categoria=ALIMENTACAO
    Então recebo apenas gastos de alimentação

  Cenário: Criar transação manual
    Quando faço POST /api/transacoes com data, descricao, categoria, valor "89.90" e tipo
    Então recebo 201 com o id criado
    E a criação usou parcela_numero=1, parcela_total=1, grupo_parcela_id UUID novo e embedding None

  Cenário: POST sem campo obrigatório
    Quando faço POST /api/transacoes sem "valor"
    Então recebo 400

  Cenário: PUT atualiza apenas campos enviados
    Dado uma transação existente
    Quando faço PUT /api/transacoes/<id> com {"valor": "75.00"}
    Então recebo 200 e o update contém apenas valor

  Cenário: PUT e DELETE com id inexistente
    Quando faço PUT ou DELETE /api/transacoes/99999
    Então recebo 404

  Cenário: Valores monetários como string
    Quando faço GET /api/transacoes
    Então todo campo "valor" é string decimal com 2 casas (nunca número JSON)
