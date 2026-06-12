# STATUS — parcelas-assinaturas

**Plano:** `plan.md` (Status: Aprovado — usuário, 12/06/2026)
**Contratos congelados:** `datas-parcela`, `repositorio-grupos`, `api-grupos`, `api-gastos-fixos`, `frontend-dashboard`
**Branch da feature:** `feature/parcelas-assinaturas`

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Base: helpers de data, repositório, listar_ativas | python | done | feature/parcelas-assinaturas | 438/438 verdes; commit e11c610 |
| 02 | Grupos: service + controller (editar/criar) | python | done | feature/parcelas-assinaturas | 479/479 verdes; commit 4cec95a |
| 03 | Gastos fixos: service + controller (CRUD) | python | done | worktree agente-financeiro-parcelas | 523/523 verdes; commit d2d7192 |
| 04 | Proxy Flask + cliente HTTP | python | done | worktree agente-financeiro-parcelas | 548/548 verdes; commit 2abffd8 |
| 05 | UI parcelas (editar/novo) | python | done | worktree agente-financeiro-parcelas | 548/548; commit c19ec7e (+base.html: block scripts) |
| 06 | UI gastos fixos (seção/CRUD) | python | done | worktree agente-financeiro-parcelas | 571/571 verdes; commit 9e7af59 (+23 testes de render) |

## Ordem de integração

1 → 2 → 3 → 4 → 5 → 6. Suíte `uv run pytest tests/ -v` verde a cada merge.
