[REQUERIMENTOS DE NEGOCIO — melhorias-cadastramento]

Origem: sessão de correção manual da base (dados-originais.txt → dados-corrigidos.txt).
O usuário consultou a base, corrigiu registro a registro e indicou como deseja que os
novos cadastros passem a se comportar.

Regras decididas:

1. Forma de pagamento
   - Formas válidas: CARTAO_CREDITO, CARTAO_DEBITO, PIX, BOLETO.
   - NUNCA cadastrar OUTRO/OUTROS.
   - Quando o usuário não informar a forma, assumir PIX.
   - Se o usuário indicou parcelas, é cartão de crédito (CARTAO_CREDITO).

2. Gastos fixos (recorrentes)
   - Quando o agente identificar que o gasto é da categoria GASTOS_FIXOS, deve
     confirmar com o usuário se pode considerar esse gasto todos os meses.
   - Confirmado, o gasto é recorrente: não usa data/parcela_numero/parcela_total e
     entra sempre na base de cálculo dos meses seguintes.

3. Categoria
   - "Parcelado" não é categoria. A parcela herda a categoria real da compra.
   - Abandonar PARCELAMENTOS.
   - Curso = categoria EDUCACAO, tipo GASTO (não INVESTIMENTO).
   - GASTOS_FIXOS reservada para assinaturas recorrentes (academia, LinkedIn,
     Spotify, Claude code Max, Google Drive).

4. Status e data
   - PIX = pago na hora (status PAGO, data real).
   - CARTAO_CREDITO = pendente até a fatura (status PENDENTE, data deslocada para o
     vencimento da fatura).

5. Valor
   - Cada registro de parcela armazena o valor da parcela (não o total).
   - Quando o total não divide exato, distribuir o resto entre as parcelas.

6. Migração / sanitização
   - Atualizar os registros existentes conforme dados-corrigidos.txt: recategorizar,
     ajustar forma de pagamento, limpar parcela dos recorrentes, remover itens de
     teste (Coxinha, Sorvete do Mac, tokens open ai, Claude code 472) e adicionar
     Google Drive e Claude code Max como recorrentes.
