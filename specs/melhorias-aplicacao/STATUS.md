# STATUS — melhorias-aplicacao

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Backend core (FastAPI + engine pooled) | python | todo | — | base; resolve a performance |
| 02 | Backend transações/resumo/parcelas/categorias | python | todo | — | depende de 01 |
| 03 | Backend gráficos/projeção (13 meses, receitas) | python | todo | — | depende de 01 |
| 04 | Frontend em camadas, proxy, layout, linha de receitas | python | todo | — | depende dos contratos |
| 05 | start.py + remoção do dashboard antigo | python | todo | — | depende de 01–04 |

DAG: `contratos → 01 → {02, 03}` ; `04` em paralelo (só contratos) ; `05` por último.
Contratos congelados: db-engine, api-endpoints, frontend-backend, projecao-13-meses.
