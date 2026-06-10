# Tarefa 03 — Categorizador e prompts refletem os novos enums

**Stack:** python
**Depende de:** 01
**Contratos:** `contracts/enums.md`

## Objetivo

Alinhar o categorizador e os prompts ao novo conjunto de categorias e formas de pagamento.

## Arquivos (posse exclusiva)

- `app/agents/categorizador.py`
- `prompts/categorizacao.md`
- `prompts/sistema.md`

## Escopo

1. `CategorizacaoResult.categoria` Literal → `ALIMENTACAO, TRANSPORTE, LAZER, EDUCACAO,
   GASTOS_FIXOS, COMPRAS, GASTOS_PONTUAIS` (sem `OUTROS`; `INVESTIMENTO`/`RECEITA` continuam
   resolvidos fora do LLM como hoje).
2. `prompts/categorizacao.md`: orientar `EDUCACAO` (cursos = GASTO/EDUCACAO), distinção
   `GASTOS_PONTUAIS` (gasto único não-recorrente, ex.: reparo/aquisição pontual) × `COMPRAS`
   (bens de consumo/objetos), e `GASTOS_FIXOS` (assinatura/mensalidade recorrente).
3. `prompts/sistema.md`: refletir formas válidas (`CARTAO_CREDITO/CARTAO_DEBITO/PIX/BOLETO`),
   sem `OUTRO`; parcelas ⇒ cartão de crédito.

## Critérios de aceite

- [ ] Literal do categorizador bate 1:1 com `contracts/enums.md` (sem `OUTROS`)
- [ ] Prompt orienta curso → `EDUCACAO`/`GASTO`
- [ ] Prompt nunca sugere `OUTRO` como forma

## Verificação local

```bash
uv run pytest tests/ -v -k "categoriz or extrator"
```
