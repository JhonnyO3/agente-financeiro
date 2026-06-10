# language: pt
# Tarefa: T06 — pytest (repository mockado)
Funcionalidade: API resumo v2 e projeção

  Cenário: Resumo com receitas e novo saldo
    Dado GASTO 350, RECEITA 5000, INVESTIMENTO 500 no período
    Quando faço GET /api/resumo
    Então gastos "350.00", receitas "5000.00", investimentos "500.00", saldo "4650.00"

  Cenário: Projeção só com pendentes
    Dado parcelas PENDENTE nos meses M+1 e M+2 e uma PAGO em M+1
    Quando faço GET /api/projecao
    Então recebo 6 meses; a PAGO não entra nas somas

  Cenário: Mês vazio vem zerado
    Quando faço GET /api/projecao sem dados
    Então 6 elementos com "0.00" e qtd_parcelas 0

  Cenário: Saldo projetado negativo
    Dado mês futuro só com gastos pendentes 750
    Então saldo_projetado "-750.00"
