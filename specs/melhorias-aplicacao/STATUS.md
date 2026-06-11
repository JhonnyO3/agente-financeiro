# STATUS — melhorias-aplicacao

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Backend core (FastAPI + engine pooled) | python | done | feat/melhorias-aplicacao | commit c6a2498 |
| 02 | Backend transações/resumo/parcelas/categorias | python | doing | feat/melhorias-aplicacao | python-dev (lote 2) |
| 03 | Backend gráficos/projeção (13 meses, receitas) | python | doing | feat/melhorias-aplicacao | python-dev (lote 2) |
| 04 | Frontend em camadas, proxy, layout, linha de receitas | python | done | feat/melhorias-aplicacao | commit 82c071b |
| 05 | start.py + remoção do dashboard antigo | python | todo | — | depende de 01–04 |

DAG: `contratos → 01 → {02, 03}` ; `04` em paralelo (só contratos) ; `05` por último.
Contratos congelados: db-engine, api-endpoints, frontend-backend, projecao-13-meses.
