# language: pt
Funcionalidade: Sanitização dos dados existentes
  Regra RF-08.

  Cenário: Nenhuma forma OUTRO permanece
    Dado um banco com registros legados usando "OUTRO" e "CARTAO"
    Quando a migração 0004 é aplicada
    Então nenhum registro tem forma_pagamento "OUTRO"
    E registros antes "CARTAO" passam a "CARTAO_CREDITO"

  Cenário: Categorias legadas são reclassificadas
    Dado registros legados em "GASTOS_FIXOS" e "PARCELAMENTOS"
    Quando a migração 0004 é aplicada
    Então nenhum registro tem categoria "PARCELAMENTOS" ou "OUTROS"
    E "curso claude code" está em "EDUCACAO"
    E "parcela do aquecedor" está em "GASTOS_PONTUAIS"

  Cenário: Recorrentes sem estrutura de parcela
    Quando a migração 0004 é aplicada
    Então "academia", "LinkedIn", "Spotify", "Google Drive" e "Claude code Max" têm recorrente verdadeiro
    E esses registros têm parcela_numero e parcela_total iguais a 1

  Cenário: Itens de teste removidos e zara isolado
    Quando a migração 0004 é aplicada
    Então "Coxinha", "Sorvete do Mac", "tokens open ai" e "Claude code" (472) não existem
    E "zara" tem um grupo_parcela_id diferente do grupo do batman

  Cenário: Migração é idempotente
    Dado que a migração 0004 já foi aplicada
    Quando a migração 0004 é aplicada novamente
    Então o número de registros e os valores permanecem inalterados
