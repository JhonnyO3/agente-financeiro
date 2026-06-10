# STATUS — melhorias-dashboard

| ID | Tarefa                                  | Stack     | Estado | Worktree/Branch | Nota |
|----|-----------------------------------------|-----------|--------|-----------------|------|
| 01 | Modelo de dados, migration, helper      | python    | done   | — (integrado)   | 18 testes; quebra esperada em test_templates (T08 corrige) |
| 02 | Extração v2                             | python    | done   | — (integrado)   | 5 testes novos |
| 03 | Cadastrar v2 (1..N, status, receitas)   | python    | done   | — (integrado)   | 14 testes |
| 04 | Marcar pago via WhatsApp                | python    | done   | — (integrado)   | + fix Literal na integração |
| 05 | Consultar/Formatador com receitas       | python    | done   | — (integrado)   |      |
| 06 | API resumo v2 + projeção                | python    | done   | — (integrado)   | 21 testes |
| 07 | API transações v2                       | python    | done   | — (integrado)   | 36 testes |
| 08 | Front base (templates, cards, projeção) | python+js | done   | — (integrado)   | corrigiu o vermelho conhecido |
| 09 | Front tabela (badges, filtro, modais)   | js        | done   | — (integrado)   | node --check OK |
| 10 | Backfill de parcelas                    | python    | done   | — (integrado)   | 15 testes |

> Lote 1: T01 · Lote 2: T02, T04–T08, T10 (paralelo) · Lote 3: T03, T09.
> **Todas as 10 tarefas integradas.** Suíte: 196 testes verdes. JS: node --check OK.
> Pendências fora do código (precisam de banco real): `alembic upgrade head`,
> `backfill_parcelas.py --dry-run` → revisar → rodar, e smoke manual no browser.
