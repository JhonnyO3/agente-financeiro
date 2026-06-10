# Tarefa 01 — Modelo de dados, migration e helper de parcelas

**Stack:** python · **Dependências:** nenhuma
**Contratos:** `contracts/modelo-dados.md`

## Objetivo
Fundação: enums novos, 4 colunas, migration 0002 com data-fix, DTOs, repository
repassando os campos, e helper puro de datas de parcela.

## Arquivos que esta tarefa possui
- `app/models/enums.py` · `app/models/transacao.py`
- `app/repositories/dtos.py` · `app/repositories/transacao_repository.py`
- `migrations/versions/0002_status_forma_responsavel_detalhes.py`
- `app/services/parcelas.py` (novo)
- `tests/test_parcelas_helper.py` (novo) · `tests/test_repository.py`

## O que implementar
Tudo exatamente como em `contracts/modelo-dados.md`. A migration usa `server_default`
nas colunas NOT NULL e o UPDATE retroativo de status. `criar`/`criar_lote` repassam os
4 campos novos. Helper com `adicionar_meses` (clamp último dia), `status_por_data`,
`datas_do_grupo`.

## Critérios de aceite
- [ ] `adicionar_meses(date(2026,1,31), 1) == date(2026,2,28)`; bissexto → 29
- [ ] `datas_do_grupo(date(2026,6,10), 2, 4) == [10/05, 10/06, 10/07, 10/08]`
- [ ] `TransacaoCreate` sem os campos novos continua construível (defaults)
- [ ] `criar` persiste os 4 campos (teste com sessão mockada conferindo o objeto)
- [ ] Migration tem upgrade com UPDATE retroativo e downgrade com drop

## Verificação
`uv run pytest tests/ -q` — suíte inteira verde (testes existentes não quebram).
