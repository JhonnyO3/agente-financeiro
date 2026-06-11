# STATUS — melhorias-aplicacao

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Backend core (FastAPI + engine pooled) | python | done | feat/melhorias-aplicacao | commit c6a2498 |
| 02 | Backend transações/resumo/parcelas/categorias | python | done | feat/melhorias-aplicacao | commit af1b0e9 |
| 03 | Backend gráficos/projeção (13 meses, receitas) | python | done | feat/melhorias-aplicacao | commit f37f219 |
| 04 | Frontend em camadas, proxy, layout, linha de receitas | python | done | feat/melhorias-aplicacao | commit 82c071b |
| 05 | start.py + remoção do dashboard antigo | python | done | feat/melhorias-aplicacao | commit T05 |

DAG: `contratos → 01 → {02, 03}` ; `04` em paralelo (só contratos) ; `05` por último. **Todas done.**

Verificação de integração: `uv run pytest -q` → 201 passed. Paridade de rotas confirmada;
`dashboard/` removido; `start.py` sobe backend:8000 + frontend:5000.
Pendente (manual, precisa de Postgres): medir endpoints <1s contra o DB real.
