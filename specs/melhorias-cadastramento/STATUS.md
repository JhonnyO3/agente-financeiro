# STATUS — melhorias-cadastramento

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Enums, coluna `recorrente`, DTOs, migration 0003 | python | done | feat/melhorias-cadastramento | base congelada; commit 0013e76 |
| 02 | Pagamento, status/data, fim PARCELAMENTOS, recorrência | python | done | feat/melhorias-cadastramento | commit d32248e |
| 03 | Categorizador + prompts | python | done | feat/melhorias-cadastramento | commit T03 |
| 04 | Dashboard reflete enums | python | done | feat/melhorias-cadastramento | commit T04 |
| 05 | Migração de sanitização (0004) | python | done | feat/melhorias-cadastramento | commit T05 |

DAG: `01 → {02, 03, 04, 05}` (02–05 em paralelo, sem colisão de arquivos). **Todas done.**

Verificação de integração: `uv run pytest tests/ -q` → 225 passed.
Pendência fora-de-escopo resolvida na integração: `api_graficos.py`/`CATEGORIAS_GASTO`
(troca OUTROS→EDUCACAO). Migração 0004 não executada contra Postgres (sem DB no ambiente).
