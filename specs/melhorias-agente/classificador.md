# Injection — Classificador

> Injetado no placeholder `{injection_acao}` do `prompt-base.md`.
> O classificador é a **única** chamada LLM de roteamento. Recebe a mensagem,
> o histórico recente e o **estado pendente** (`{estado_pendente}`), e retorna
> uma intenção estruturada (structured output, schema Pydantic).

## Sua tarefa

Identificar a intenção da mensagem do usuário e extrair os parâmetros básicos.

## Contexto recebido

| Variável | Conteúdo |
|---|---|
| `{historico_recente}` | Últimas 5 mensagens da conversa |
| `{estado_pendente}` | Resumo da pendência ativa, ou "nenhuma". Ex: "cadastro aguardando confirmação", "cadastro aguardando valor", "lista de 3 opções exibida (1. Internet, 2. Zara, 3. Batman)", "exclusão aguardando escopo (1. somente este, 2. todos)" |

## Intenções possíveis (10)

### Operações

| Intenção | Quando usar |
|---|---|
| `cadastrar` | Usuário informa gasto(s), despesa(s), investimento ou receita — **um ou vários na mesma mensagem** (itens viram lista em `parametros.itens`) |
| `listar` | Usuário quer ver, consultar, somar ou resumir registros — **qualquer pergunta que exija números do banco**: "listar gastos", "quanto gastei esse mês?", "qual meu maior gasto?", "estou no azul?", "extrato" |
| `atualizar` | Corrigir/editar campo de registro existente — **inclui marcar como pago/quitado** (atualização de status): "muda a zara pra 200", "paguei a internet" |
| `excluir` | Apagar registro(s) — individual ("apaga o gasto das flores") **ou em massa por filtro** ("apaga tudo de maio", "remove todos de transporte") |
| `conversar` | Diálogo financeiro **sem cálculo nem consulta ao banco**: orientação, explicação, conceito, conversa sobre finanças. Ex: "vale a pena parcelar?", "como funciona o cadastro?", "me dá uma dica pra economizar" |

### Respostas a pendência (só válidas quando `{estado_pendente}` ≠ "nenhuma")

| Intenção | Quando usar |
|---|---|
| `confirmar` | "confirmar", "sim", "pode salvar", "ok", "isso" |
| `cancelar` | "cancelar", "não", "para", "deixa pra lá" |
| `selecionar` | Escolha entre opções exibidas — número ("2") **ou** texto que corresponde a uma opção ("todos", "a primeira", "somente este") |
| `complementar` | Fornece dado faltante da pendência: "foi 350", "em 3x", "à vista", "no crédito" |

### Fallback

| Intenção | Quando usar |
|---|---|
| `desconhecida` | Fora do escopo financeiro ("me conta uma piada") **ou** confiança < 0.7 |

## Regra de fronteira — `listar` × `conversar`

- Precisa de **números, registros ou cálculo**? → `listar` (rota determinística: SQL + template).
- É **conversa pura** (conceito, opinião, orientação, small talk financeiro)? → `conversar`.
- Na dúvida entre as duas → `listar`.

## Regras de pendência

1. Se `{estado_pendente}` = "nenhuma", **nunca** retorne `confirmar`, `cancelar`, `selecionar` ou `complementar`.
2. Se há pendência mas a mensagem é claramente uma **intenção nova** ("gastei 30 no uber" durante uma confirmação), classifique a intenção nova — o roteador cancela a pendência e segue.
3. Se há pendência e a mensagem é ambígua entre resposta e intenção nova, prefira a leitura como resposta à pendência.

## Saída — structured output (Pydantic)

```python
class Intencao(BaseModel):
    acao: Literal[
        "cadastrar", "listar", "atualizar", "excluir", "conversar",
        "confirmar", "cancelar", "selecionar", "complementar",
        "desconhecida",
    ]
    parametros: ParametrosPorAcao   # union discriminada — schema tipado por ação
    confianca: float                # 0.0 a 1.0
```

Parâmetros por ação (campos não mencionados → `null`):

| Ação | Parâmetros |
|---|---|
| `cadastrar` | `itens: [{descricao, valor, forma_pagamento, parcela_atual, total_parcelas, dia_vencimento, data, tipo}]` |
| `listar` | `periodo, categoria, responsavel, status` |
| `atualizar` | `referencia (descricao/data/valor que identifica o registro), campo, novo_valor` |
| `excluir` | `referencia` (registro específico) **ou** `periodo/categoria` (lote) |
| `conversar` | `{}` (a mensagem original segue para a Tool) |
| `selecionar` | `opcao: int` (mapear texto para o número da opção pendente) |
| `complementar` | `campo, valor` (ex: `campo=parcelas, valor=3` · `campo=valor, valor=350`) |
| demais | `{}` |

## Regras de extração

- `valor` → número, sem símbolo de moeda
- `periodo` → `"mes_atual"`, `"mes_passado"`, `"YYYY-MM"`, ou nome do mês
- `confianca < 0.7` → retornar `desconhecida`
- Nunca inferir intenção além do que foi dito
- Nunca calcular nada (totais, divisão de parcelas) — só extrair o que está na mensagem

## Exemplos

| Mensagem | Estado pendente | Saída |
|---|---|---|
| "Gastei 472 reais com Claude code" | nenhuma | `{acao: cadastrar, parametros: {itens: [{descricao: "Claude Code", valor: 472}]}, confianca: 0.98}` |
| "140 das flores e 190 de internet ontem" | nenhuma | `{acao: cadastrar, parametros: {itens: [{descricao: "Flores", valor: 140}, {descricao: "Internet", valor: 190, data: "ontem"}]}, confianca: 0.96}` |
| "listar gastos" | nenhuma | `{acao: listar, parametros: {periodo: "mes_atual"}, confianca: 0.99}` |
| "quanto gastei esse mês?" | nenhuma | `{acao: listar, parametros: {periodo: "mes_atual"}, confianca: 0.97}` |
| "estou no azul esse mês?" | nenhuma | `{acao: listar, parametros: {periodo: "mes_atual"}, confianca: 0.92}` |
| "vale a pena parcelar uma compra grande?" | nenhuma | `{acao: conversar, parametros: {}, confianca: 0.93}` |
| "corrige o valor da zara para 200" | nenhuma | `{acao: atualizar, parametros: {referencia: "zara", campo: "valor", novo_valor: 200}, confianca: 0.96}` |
| "paguei a internet" | nenhuma | `{acao: atualizar, parametros: {referencia: "internet", campo: "status", novo_valor: "PAGO"}, confianca: 0.94}` |
| "apaga o gasto das flores" | nenhuma | `{acao: excluir, parametros: {referencia: "flores"}, confianca: 0.95}` |
| "apaga tudo de maio" | nenhuma | `{acao: excluir, parametros: {periodo: "2026-05"}, confianca: 0.95}` |
| "confirmar" | cadastro aguardando confirmação | `{acao: confirmar, parametros: {}, confianca: 0.99}` |
| "não, deixa" | exclusão aguardando confirmação | `{acao: cancelar, parametros: {}, confianca: 0.98}` |
| "2" | lista de 3 opções exibida | `{acao: selecionar, parametros: {opcao: 2}, confianca: 0.99}` |
| "todos" | exclusão aguardando escopo (1. somente este, 2. todos) | `{acao: selecionar, parametros: {opcao: 2}, confianca: 0.97}` |
| "foi 350" | cadastro aguardando valor | `{acao: complementar, parametros: {campo: "valor", valor: 350}, confianca: 0.97}` |
| "em 3x" | cadastro aguardando parcelas | `{acao: complementar, parametros: {campo: "parcelas", valor: 3}, confianca: 0.97}` |
| "gastei 30 no uber" | exclusão aguardando confirmação | `{acao: cadastrar, parametros: {itens: [{descricao: "Uber", valor: 30}]}, confianca: 0.95}` ← intenção nova vence pendência |
| "me conta uma piada" | nenhuma | `{acao: desconhecida, parametros: {}, confianca: 0.99}` |

## Mapeamento — intenções de hoje → novas

| Hoje (código atual) | Novo |
|---|---|
| `CADASTRAR` | `cadastrar` |
| `CADASTRAR_LOTE` | `cadastrar` (itens em lista) |
| `CONSULTAR` | `listar` |
| `ALTERAR` | `atualizar` |
| `MARCAR_PAGO` | `atualizar` (campo=status) |
| `EXCLUIR` | `excluir` (referência nominal) |
| `EXCLUIR_LOTE` | `excluir` (filtros de período/categoria) |
| `FORA_DE_ESCOPO` | `desconhecida` |
| — (inexistente) | `conversar` |
| ConfirmacaoChain "sim"/"não" | `confirmar` / `cancelar` |
| ConfirmacaoChain "parcela"/"grupo" | `selecionar` (opções numeradas) |
| Estados `AGUARDAR_PARCELAS`/`AGUARDAR_RECORRENCIA` | `complementar` |
