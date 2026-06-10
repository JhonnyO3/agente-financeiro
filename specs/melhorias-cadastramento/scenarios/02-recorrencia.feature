# language: pt
Funcionalidade: Confirmação de gasto recorrente
  Regra RF-06.

  Cenário: GASTOS_FIXOS dispara confirmação de recorrência
    Dado que o cadastro foi categorizado como "GASTOS_FIXOS"
    Quando o agente responde ao usuário
    Então o agente pergunta se pode considerar o gasto todos os meses
    E o estado "AGUARDAR_RECORRENCIA" é salvo para o número

  Cenário: Usuário confirma recorrência
    Dado o estado "AGUARDAR_RECORRENCIA" salvo
    Quando o usuário responde "sim"
    Então o registro é gravado com recorrente igual a verdadeiro
    E parcela_numero e parcela_total são 1

  Cenário: Usuário nega recorrência
    Dado o estado "AGUARDAR_RECORRENCIA" salvo
    Quando o usuário responde "não"
    Então o registro é gravado com recorrente igual a falso
