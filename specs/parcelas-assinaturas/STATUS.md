# STATUS — parcelas-assinaturas

**Plano:** `plan.md` (Status: Aprovado — usuário, 12/06/2026)
**Contratos congelados:** `datas-parcela`, `repositorio-grupos`, `api-grupos`, `api-gastos-fixos`, `frontend-dashboard`
**Branch da feature:** `feature/parcelas-assinaturas`

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Base: helpers de data, repositório, listar_ativas | python | doing | feature/parcelas-assinaturas | execução sequencial (DAG linear) direto na branch |
| 02 | Grupos: service + controller (editar/criar) | python | todo | — | depende de 01 |
| 03 | Gastos fixos: service + controller (CRUD) | python | todo | — | depende de 02 (via `backend/main.py`/CONTROLLERS) |
| 04 | Proxy Flask + cliente HTTP | python | todo | — | depende de 02 e 03 |
| 05 | UI parcelas (editar/novo) | python | todo | — | depende de 04; dono de `index.html`/`app.js` |
| 06 | UI gastos fixos (seção/CRUD) | python | todo | — | depende de 05 (via include do partial + script) |

## Ordem de integração

1 → 2 → 3 → 4 → 5 → 6. Suíte `uv run pytest tests/ -v` verde a cada merge.
