# STATUS — melhorias-cadastramento

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Enums, coluna `recorrente`, DTOs, migration 0003 | python | doing | feat/melhorias-cadastramento | base; congela contratos |
| 02 | Pagamento, status/data, fim PARCELAMENTOS, recorrência | python | todo | — | depende de 01 |
| 03 | Categorizador + prompts | python | todo | — | depende de 01 |
| 04 | Dashboard reflete enums | python | todo | — | depende de 01 |
| 05 | Migração de sanitização (0004) | python | todo | — | depende de 01 |

DAG: `01 → {02, 03, 04, 05}` (02–05 em paralelo, sem colisão de arquivos).
