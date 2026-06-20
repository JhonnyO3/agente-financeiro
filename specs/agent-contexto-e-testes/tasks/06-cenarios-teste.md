# Tarefa 06 — Suite de 60 cenários de teste (`scripts/cenarios_teste.jsonl`)

**Stack:** python  
**Estado:** todo  
**Depende de:** 05 (harness precisa existir para validar)  
**Bloqueia:** nenhuma

## Objetivo

Criar `scripts/cenarios_teste.jsonl` com 60 cenários divididos em 20 gastos, 20 investimentos/receitas e 20 consultas.

## Arquivos que esta tarefa possui

- `scripts/cenarios_teste.jsonl` ← criar

## NÃO toca em

- Nenhum arquivo Python

## Formato

Cada linha é um objeto JSON. Um cenário pode ter múltiplos turnos (mesmo `cenario`, `turno` diferente).

```jsonl
{"cenario": N, "turno": T, "msg": "...", "espera": "..." }
```

- `espera`: substring case-insensitive buscada na resposta; `null` = só verifica que não houve exceção.

## Distribuição dos 60 cenários

### Gastos (cenários 1–20)

| # | Descrição | Turno(s) | espera |
|---|---|---|---|
| 1 | Gasto simples PIX | 1 | "confirmar" ou "cadastr" |
| 2 | Gasto no cartão de crédito | 1 | "crédit" ou "cartão" |
| 3 | Gasto parcelado 3x | 1 | "3x" ou "parcel" |
| 4 | Gasto ambíguo (sem forma) → pergunta forma | 1 | "pix" or "cartão" ou "débito" |
| 5 | Multi-turno: informa gasto sem valor / informa valor | 2 | null |
| 6 | Multi-turno: informa gasto sem forma / informa "no crédito" | 2 | "crédit" |
| 7 | Gasto com vencimento dia 10 → CARTAO_CREDITO | 1 | "crédit" ou "cartão" |
| 8 | Gasto de alimentação | 1 | "ALIMENTACAO" ou "aliment" |
| 9 | Gasto de transporte (uber) | 1 | "TRANSPORTE" ou "transport" |
| 10 | Gasto de lazer | 1 | "LAZER" ou "lazer" |
| 11 | Gasto de compras (roupa) | 1 | "COMPRAS" ou "roupa" |
| 12 | Gasto de gastos_fixos (netflix) | 1 | "GASTOS_FIXOS" ou "netflix" |
| 13 | Dois gastos numa mensagem | 1 | "confirmar" |
| 14 | Gasto com dinheiro | 1 | "PIX" ou "dinheiro" |
| 15 | Gasto parcelado 12x com vencimento | 1 | "12x" ou "parcel" |
| 16 | Gasto no débito | 1 | "débito" ou "CARTAO_DEBITO" |
| 17 | Gasto de educação (curso) | 1 | "EDUCACAO" ou "educaç" |
| 18 | Gasto pontual (conserto) | 1 | "GASTOS_PONTUAIS" ou "conserto" |
| 19 | Cancelamento após confirmação pendente | 2 | "cancel" ou "ok" |
| 20 | Gasto + confirma | 2 | "salvo" ou "cadastr" ou "registr" |

### Investimentos e receitas (cenários 21–40)

| # | Descrição | espera |
|---|---|---|
| 21 | Aporte em fundo de renda fixa | "INVESTIMENTO" ou "invest" |
| 22 | Aporte em CDB | "INVESTIMENTO" |
| 23 | Aporte em poupança | "INVESTIMENTO" |
| 24 | Compra de ação | "INVESTIMENTO" |
| 25 | Salário recebido | "RECEITA" ou "salário" |
| 26 | Freelance recebido | "RECEITA" |
| 27 | Dividendos recebidos | "RECEITA" |
| 28 | Venda de ativo | "RECEITA" ou "INVESTIMENTO" |
| 29 | Tesouro direto | "INVESTIMENTO" |
| 30 | Aporte em ETF | "INVESTIMENTO" |
| 31 | LCI recebido | "INVESTIMENTO" ou "RECEITA" |
| 32 | Multi-turno: investimento sem valor / valor informado | null |
| 33 | Renda variável (FII) | "INVESTIMENTO" |
| 34 | Bônus de trabalho | "RECEITA" |
| 35 | Estorno recebido | "RECEITA" |
| 36 | Aporte parcelado (financiamento) | "INVESTIMENTO" |
| 37 | Investimento + confirma | "registr" ou "salvo" |
| 38 | Receita + confirma | "registr" ou "salvo" |
| 39 | Aporte em bitcoin/cripto | "INVESTIMENTO" |
| 40 | Pensão/aluguel recebido | "RECEITA" |

### Consultas (cenários 41–60)

| # | Descrição | espera |
|---|---|---|
| 41 | "quanto gastei esse mês?" | "R$" ou "mês" |
| 42 | "me mostra os parcelamentos" | "parcel" ou "crédit" |
| 43 | "estou no azul?" | "R$" ou "saldo" ou "azul" |
| 44 | "gastos de alimentação" | "aliment" |
| 45 | "gastos dessa semana" | "semana" ou "R$" |
| 46 | "quanto gastei ontem?" | "ontem" ou "R$" |
| 47 | "extrato do mês" | "R$" |
| 48 | "qual meu maior gasto?" | "R$" |
| 49 | "gastos de transporte" | "transport" |
| 50 | "gastos pendentes" | "pendens" ou "pendente" |
| 51 | "gastei hoje?" | "hoje" ou "R$" |
| 52 | "resumo financeiro" | "R$" |
| 53 | "gastos pagos esse mês" | "pago" ou "R$" |
| 54 | "quanto investi?" | "invest" ou "R$" |
| 55 | "qual minha receita esse mês?" | "receita" ou "R$" |
| 56 | "gastos de maio" | "maio" ou "R$" |
| 57 | "gastos no dia 10" | "R$" |
| 58 | "me mostra tudo" | "R$" |
| 59 | Conversar: "vale a pena parcelar?" | "parcel" ou "crédit" |
| 60 | Conversar: "dica para economizar" | "economiz" ou "dica" |

## Critério de verificação local

```bash
# Contar linhas (deve ser >= 60):
wc -l scripts/cenarios_teste.jsonl

# Validar JSON de cada linha:
python -c "
import json
with open('scripts/cenarios_teste.jsonl') as f:
    for i, line in enumerate(f, 1):
        json.loads(line)
print('JSON válido em todas as linhas')
"

# Rodar no harness (exige LLM real ou seed):
uv run python scripts/chat_terminal.py --batch scripts/cenarios_teste.jsonl
```
