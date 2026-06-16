# language: pt
Funcionalidade: Parser de período natural
  Resolve a string de período para (inicio, fim, label) sem nunca falhar.
  Contexto fixo: hoje = 15/06/2026 (segunda-feira), fuso do usuário.

  Cenário: hoje resolve para o dia corrente
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "hoje"
    Então recebo início 15/06/2026, fim 15/06/2026 e label "hoje"

  Cenário: ontem resolve para o dia anterior
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "ontem"
    Então recebo início 14/06/2026, fim 14/06/2026 e label "ontem"

  Cenário: semana atual vai de segunda a domingo
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "semana_atual"
    Então recebo início 15/06/2026 (segunda), fim 21/06/2026 (domingo) e label "semana atual"

  Cenário: semana atual quando hoje é domingo
    Dado um relógio fixado em 21/06/2026 (domingo)
    Quando parseio o período "semana_atual"
    Então recebo início 15/06/2026 (segunda), fim 21/06/2026 (domingo)

  Cenário: semana passada é a semana anterior completa
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "semana_passada"
    Então recebo início 08/06/2026 (segunda), fim 14/06/2026 (domingo) e label "semana passada"

  Cenário: mês atual sem período informado
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período None
    Então recebo início 01/06/2026, fim 30/06/2026 e label "Jun/2026"

  Cenário: mês atual explícito
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "mes_atual"
    Então recebo início 01/06/2026, fim 30/06/2026 e label "Jun/2026"

  Cenário: mês passado não cai em fallback
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "mes_passado"
    Então recebo início 01/05/2026, fim 31/05/2026 e label "Mai/2026"

  Cenário: mês passado na virada de ano
    Dado um relógio fixado em 10/01/2026
    Quando parseio o período "mes_passado"
    Então recebo início 01/12/2025, fim 31/12/2025 e label "Dez/2025"

  Cenário: formato YYYY-MM resolve o mês inteiro
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "2026-05"
    Então recebo início 01/05/2026, fim 31/05/2026 e label "Mai/2026"

  Cenário: formato YYYY-MM-DD resolve a data exata
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "2026-06-15"
    Então recebo início 15/06/2026, fim 15/06/2026 e label "15/06/2026"

  Cenário: nome de mês em português usa o ano corrente
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "junho"
    Então recebo início 01/06/2026, fim 30/06/2026 e label "Jun/2026"

  Cenário: nome de mês com e sem acento
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "março"
    Então recebo início 01/03/2026, fim 31/03/2026 e label "Mar/2026"
    E parsear "marco" produz o mesmo resultado

  Cenário: valor desconhecido faz fallback para o mês atual
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "valor_invalido"
    Então recebo início 01/06/2026, fim 30/06/2026 e label "Jun/2026"
    E nenhuma exceção é levantada

  Cenário: mês inválido em YYYY-MM cai em fallback
    Dado um relógio fixado em 15/06/2026
    Quando parseio o período "2026-13"
    Então recebo o mês atual como fallback sem exceção
