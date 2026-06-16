# STATUS — parser-periodo-e-templates

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | Parser de período (`parsear_periodo`) | python | todo | — | — |
| 02 | Wiring de `ToolListar` ao parser | python | todo | — | depende de 01 |
| 03 | Vocabulário de período no prompt do classificador | python | todo | — | — |
| 04 | Template loader + diretório `templates/` | python | todo | — | — |
| 05 | Refatorar `Formatador` para usar templates | python | todo | — | depende de 04 |

DAG: `parser-periodo.md → 01 → 02` ; `03` em paralelo (só contrato) ;
`template-loader.md → 04 → 05`. Features F1 (01,02,03) e F2 (04,05) independentes.

Gate humano: `plan.md` em **Rascunho**. A squad só executa após aprovação.
