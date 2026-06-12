# Injection — Extração de Atualização

Extraia apenas os campos que o usuário deseja modificar em uma transação financeira.

## Candidatos encontrados (via busca semântica)

{candidatos}

## Parâmetros do classificador

{parametros}

## Regras

- Campos não mencionados pelo usuário → null (nunca invente valores)
- Se o usuário disser "paguei" ou "quitei" → novo_valor para o campo status = "PAGO"
- Se o usuário mencionar um novo valor monetário → novo_valor para o campo valor (número sem símbolo de moeda)
- Se o usuário mencionar uma nova descrição → novo_valor para o campo descricao
- Se o usuário mencionar uma nova data → novo_valor para o campo data (formato ISO YYYY-MM-DD)
- Se o usuário mencionar uma nova categoria → novo_valor para o campo categoria (usar enum válido)
- Identifique qual candidato da lista melhor corresponde à referência do usuário

## Campos possíveis de alterar

valor · descricao · categoria · data · status · forma_pagamento · responsavel
