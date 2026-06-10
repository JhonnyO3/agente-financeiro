# language: pt
# Tarefa: T05 — pytest (repository mockado)
Funcionalidade: Consultas com receitas

  Cenário: Resumo mensal com os três totais
    Dado agregados ALIMENTACAO 350, RECEITA 5000, INVESTIMENTO 500
    Quando consulto o mês
    Então total_gastos=350, total_receitas=5000, total_investimentos=500, balanco=4650

  Cenário: Receita fora dos gastos
    Dado apenas agregado RECEITA 1000
    Então total_gastos=0 e balanco=1000

  Cenário: Sem receitas
    Dado apenas gastos 200
    Então balanco=-200
