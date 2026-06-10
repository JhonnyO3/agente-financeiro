# language: pt
Funcionalidade: Forma de pagamento, status e data no cadastro
  Regras RF-02, RF-03, RF-07.

  Cenário: Forma não informada assume PIX
    Dado que o usuário envia "Gastei 50 no almoço"
    Quando o cadastro é processado
    Então a forma de pagamento é "PIX"
    E o status é "PAGO"
    E a data é a data informada

  Cenário: Parcelas implicam cartão de crédito
    Dado que o usuário envia "Comprei um fone em 3x de 100"
    Quando o cadastro é processado
    Então a forma de pagamento é "CARTAO_CREDITO"
    E o status é "PENDENTE"
    E a data da primeira parcela é deslocada um mês à frente

  Cenário: Débito é pago na hora
    Dado que o usuário envia "Paguei 80 no débito no mercado"
    Quando o cadastro é processado
    Então a forma de pagamento é "CARTAO_DEBITO"
    E o status é "PAGO"

  Cenário: Soma das parcelas preserva o total
    Dado um cadastro de 100 em 3 parcelas
    Quando os valores das parcelas são calculados
    Então a soma das 3 parcelas é exatamente 100
