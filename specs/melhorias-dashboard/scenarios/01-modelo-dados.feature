# language: pt
# Tarefa: T01 — pytest
Funcionalidade: Modelo de dados v2 e helper de parcelas

  Cenário: Adicionar meses preserva o dia com clamp
    Quando adiciono 1 mês a 31/01/2026
    Então o resultado é 28/02/2026
    E adicionando 1 mês a 31/01/2024 (bissexto) o resultado é 29/02/2024

  Cenário: Datas do grupo a partir da parcela atual
    Quando calculo datas_do_grupo(10/06/2026, parcela_atual=2, parcela_total=4)
    Então recebo [10/05/2026, 10/06/2026, 10/07/2026, 10/08/2026]

  Cenário: Status por data
    Então status_por_data(ontem) é PAGO e status_por_data(amanhã) é PENDENTE

  Cenário: DTOs retrocompatíveis
    Quando construo TransacaoCreate sem os campos novos
    Então status=PENDENTE, forma_pagamento=OUTRO, responsavel="Jhonatas", detalhes=None

  Cenário: Repository persiste os campos novos
    Quando chamo criar com status=PAGO e responsavel="Mãe"
    Então o objeto Transacao adicionado à sessão contém esses valores
