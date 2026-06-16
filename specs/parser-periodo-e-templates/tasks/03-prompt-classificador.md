# Tarefa 03 — Vocabulário de período no prompt do classificador

**Stack:** python
**Depende de:** `parser-periodo.md` (congelado)
**Contrato:** `contracts/parser-periodo.md`

## Objetivo

Atualizar `agent/prompts/01-classificador.md` para que o LLM produza os valores de `periodo` que o
parser entende — eliminando a causa raiz do bug ("hoje" virava `mes_atual`).

## Arquivos (posse exclusiva)

- `agent/prompts/01-classificador.md`

## Escopo

1. Na seção "Regras de extração", trocar a linha de `periodo` (atual: `"mes_atual", "mes_passado",
   "YYYY-MM", ou nome do mês`) pelo vocabulário completo: `hoje`, `ontem`, `semana_atual`,
   `semana_passada`, `mes_atual`, `mes_passado`, `YYYY-MM`, `YYYY-MM-DD`, nome de mês PT, com a
   descrição de quando usar cada um (ver spec § "Atualização do prompt do classificador").
2. Adicionar à tabela de "Exemplos" as linhas: "quanto eu gastei hoje?" → `periodo="hoje"`;
   "o que gastei ontem?" → `periodo="ontem"`; "gastos dessa semana" → `periodo="semana_atual"`;
   "resumo da semana passada" → `periodo="semana_passada"`; "quanto gastei no dia 10?" →
   `periodo="2026-06-10"`; "gastos de maio" → `periodo="2026-05"`.
3. **Não** introduzir chaves `{`/`}` literais (o prompt é carregado via `str.format` em `prompts.py`).

## Critérios de aceite → teste

- [ ] `grep "semana_atual" agent/prompts/01-classificador.md` → presente
- [ ] `grep "mes_passado" agent/prompts/01-classificador.md` → presente na regra de extração
- [ ] Linha de `periodo` lista os 9 valores do vocabulário
- [ ] Tabela de exemplos contém os 6 novos casos
- [ ] `tests/test_prompts.py` (carregamento de prompts) continua verde — sem `{`/`}` literais quebrando `str.format`

## Verificação local

```bash
uv run pytest tests/test_prompts.py -v
```
