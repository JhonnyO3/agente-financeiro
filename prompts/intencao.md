# Prompt: Classificação de Intenção

Dado o texto da mensagem do usuário, classifique a intenção em uma das opções abaixo.
Retorne apenas o JSON — sem explicação adicional.

## Intenções possíveis

- `CADASTRAR`: usuário quer registrar um gasto ou investimento
- `ALTERAR`: usuário quer modificar um registro existente
- `EXCLUIR`: usuário quer remover um registro existente
- `CONSULTAR`: usuário quer ver resumos, totais ou histórico
- `FORA_DE_ESCOPO`: mensagem não relacionada a finanças

## Saída esperada

```json
{
  "intencao": "CADASTRAR",
  "confianca": "alta"
}
```

`confianca` pode ser `alta`, `media` ou `baixa`.
Quando `baixa`, o agente deve pedir esclarecimento antes de agir.

## Exemplos

| Mensagem                               | Intenção     |
|----------------------------------------|--------------|
| "gastei 50 no mercado"                 | CADASTRAR    |
| "comprei PETR4 por 300 reais"          | CADASTRAR    |
| "muda o gasto do uber de ontem"        | ALTERAR      |
| "apaga o lançamento do cinema"         | EXCLUIR      |
| "quanto gastei esse mês?"              | CONSULTAR    |
| "resumo de maio"                       | CONSULTAR    |
| "oi, tudo bem?"                        | FORA_DE_ESCOPO |
