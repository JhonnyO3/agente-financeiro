# Prompt: Classificação de Intenção

Dado o texto da mensagem do usuário, classifique a intenção em uma das opções abaixo.
Retorne apenas o JSON — sem explicação adicional.

## Intenções possíveis

- `CADASTRAR`: usuário quer registrar **um único** gasto ou investimento
- `CADASTRAR_LOTE`: usuário quer registrar **múltiplos** gastos de uma vez (lista, bullet points, vários itens separados por quebra de linha)
- `ALTERAR`: usuário quer modificar dados de um registro existente (valor, descrição, categoria, data)
- `MARCAR_PAGO`: usuário informa que **pagou/quitou** um lançamento já registrado (quer marcar o status como pago, sem alterar outros dados)
- `EXCLUIR`: usuário quer remover **um** registro específico existente
- `EXCLUIR_LOTE`: usuário quer remover **múltiplos** registros de uma vez (ex: "todos do mês", "todos de alimentação", "apaga tudo")
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

## Regras de desambiguação

- `MARCAR_PAGO` vs `ALTERAR`: "paguei/quitei X" sem novos dados → `MARCAR_PAGO`;
  se o usuário pede para mudar valor, descrição, categoria ou data → `ALTERAR`.
- `MARCAR_PAGO` vs `CADASTRAR`: "paguei 50 no estacionamento" (menciona valor de um
  gasto novo) → `CADASTRAR`; "paguei o estacionamento" (referência a algo já
  registrado, sem valor) → `MARCAR_PAGO`.

## Exemplos

| Mensagem                               | Intenção     |
|----------------------------------------|--------------|
| "gastei 50 no mercado"                 | CADASTRAR    |
| "cadastre esses gastos: uber 30, mercado 80, netflix 45" | CADASTRAR_LOTE |
| lista com vários itens e valores       | CADASTRAR_LOTE |
| "comprei PETR4 por 300 reais"          | CADASTRAR    |
| "muda o gasto do uber de ontem"        | ALTERAR      |
| "corrige o valor do mercado para 90"   | ALTERAR      |
| "paguei o jogo do batman"              | MARCAR_PAGO  |
| "quita a parcela do celular"           | MARCAR_PAGO  |
| "já paguei a fatura do cartão"         | MARCAR_PAGO  |
| "apaga o lançamento do cinema"         | EXCLUIR      |
| "deleta todos os gastos de junho"      | EXCLUIR_LOTE |
| "apaga tudo do mês passado"            | EXCLUIR_LOTE |
| "remove todos os gastos de alimentação"| EXCLUIR_LOTE |
| "limpa todos os meus registros"        | EXCLUIR_LOTE |
| "quanto gastei esse mês?"              | CONSULTAR    |
| "resumo de maio"                       | CONSULTAR    |
| "oi, tudo bem?"                        | FORA_DE_ESCOPO |
