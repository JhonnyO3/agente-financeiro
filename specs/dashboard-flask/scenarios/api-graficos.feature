# language: pt
# Tarefa: T03 — testes automatizados (pytest, repository mockado)
Funcionalidade: APIs de gráficos temporais

  Cenário: Mensal sempre retorna 6 meses
    Dado transações de gasto apenas em 2 dos últimos 6 meses
    Quando faço GET /api/grafico/mensal
    Então recebo exatamente 6 elementos em ordem cronológica crescente
    E cada elemento contém as 7 categorias de gasto, com "0.00" onde não há dados

  Cenário: Mensal ignora o período e investimentos
    Dado um INVESTIMENTO nos últimos 6 meses
    Quando faço GET /api/grafico/mensal?periodo=tudo
    Então o investimento não entra em nenhuma soma

  Cenário: Label de mês em português
    Dado um gasto em junho de 2026
    Quando faço GET /api/grafico/mensal
    Então o label do mês é "Jun/26"

  Cenário: Evolução só traz meses com dados
    Dado gastos em Jan/26 e Mar/26 e investimento em Mar/26
    Quando faço GET /api/grafico/evolucao
    Então recebo 2 elementos: Jan/26 (gastos>0, investimentos "0.00") e Mar/26 (ambos > 0)
    E em ordem cronológica crescente
