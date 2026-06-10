# language: pt
# Tarefa: T01 — testes automatizados (pytest)
Funcionalidade: Resolução de período e infraestrutura Flask

  Cenário: Período mês atual
    Dado que hoje é 2026-06-10
    Quando resolvo o período "mes_atual"
    Então o início é 2026-06-01 e o fim é 2026-06-10

  Cenário: Período mês anterior
    Dado que hoje é 2026-06-10
    Quando resolvo o período "mes_anterior"
    Então o início é 2026-05-01 e o fim é 2026-05-31

  Cenário: Período tudo usa o piso
    Quando resolvo o período "tudo"
    Então o início é 2000-01-01 e o fim é hoje

  Cenário: Período inválido usa fallback seguro
    Quando resolvo o período "banana"
    Então o resultado é igual ao de "mes_atual" e nenhuma exceção é lançada

  Cenário: Health check
    Dado que a aplicação Flask foi criada
    Quando faço GET /health
    Então recebo 200 com corpo {"ok": true}
