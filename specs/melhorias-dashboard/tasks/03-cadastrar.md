# Tarefa 03 — Cadastrar v2 (geração 1..N, status, receitas)

**Stack:** python · **Dependências:** 01, 02
**Contratos:** `contracts/modelo-dados.md`, `contracts/extracao-v2.md`

## Arquivos que esta tarefa possui
- `app/services/cadastrar.py` · `prompts/categorizacao.md` · `tests/test_service_cadastrar.py`

## O que implementar
Em `_processar` (e coerentemente em `executar_lote`):
1. **Datas**: substituir `data_base + timedelta(days=30*i)` por
   `datas_do_grupo(extracao.data_referencia, extracao.parcela_atual, parcela_total)`
   de `app/services/parcelas.py`
2. **Geração 1..N**: sempre todas as parcelas (a atual e as passadas incluídas),
   `status = status_por_data(data_parcela)` para cada uma
3. **Valor**: se `extracao.valor_por_parcela` presente → todas as parcelas com esse
   valor; senão divide `valor_total` com resto na última (regra atual)
4. **Categoria**: `parcela_total > 1` → força `CategoriaEnum.PARCELAMENTOS` (não chama
   categorizador à toa); `tipo == RECEITA` → força `CategoriaEnum.RECEITA`
5. **Status à vista**: `forma_pagamento == PIX` → PAGO; RECEITA com data ≤ hoje → PAGO;
   senão `status_por_data`
6. **Campos novos** no `TransacaoCreate`: status, forma_pagamento, responsavel, detalhes
7. Mensagem de resposta cita parcelas geradas (ex.: "4 parcelas registradas, 1 já paga")
8. `prompts/categorizacao.md`: mencionar que PARCELAMENTOS/RECEITA são atribuídas
   pelo sistema (o categorizador não deve retorná-las)

## Critérios de aceite
- [ ] "parcela 2/4" → 4 `TransacaoCreate` no mesmo grupo, datas 10/05..10/08, 1ª PAGO
- [ ] valor_por_parcela=200 → 4×200; valor_total=900 6x → divide com resto na última
- [ ] PIX → PAGO; cartão → PENDENTE; receita hoje → PAGO
- [ ] parcela_total>1 → categoria PARCELAMENTOS; receita → categoria RECEITA
- [ ] Fluxo AGUARDAR_PARCELAS (executar_com_parcelas_confirmadas) continua verde

## Verificação
`uv run pytest tests/test_service_cadastrar.py -v` e suíte completa verde.
