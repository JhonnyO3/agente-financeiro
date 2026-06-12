# STATUS — melhorias-agente

**Plano:** `plan.md` (Status: Aprovado — gate humano liberado em 12/06/2026; D1 ajustada para Redis por decisão do humano)
**Contratos:** intencao-schema · estado-store · resultado-tools · rag-busca · webhook-fila · prompts-injection · relogio-contexto

## Contratos

| Contrato | Status |
|---|---|
| intencao-schema | Congelado |
| estado-store | Congelado |
| resultado-tools | Congelado |
| rag-busca | Congelado |
| webhook-fila | Congelado |
| prompts-injection | Congelado |
| relogio-contexto | Congelado |

## Tarefas

| ID | Tarefa | Stack | Depende de | Estado | Worktree/Branch | Nota |
|----|--------|-------|-----------|--------|-----------------|------|
| 00 | Congelar contratos (gate) | — | plan aprovado | done | — | 7/7 Congelados (verificado 12/06) |
| 01 | Domínio: Intencao + ParametrosPorAcao + ResultadoTool | python | 00 | done | task/01 — integrado | |
| 02 | Estado: EstadoConversa + EstadoStore (Redis + memória) | python | 00 | done | task/02 — integrado | |
| 03 | Relógio injetável + novas Settings | python | 00 | done | task/03 — integrado | |
| 04 | Repository: múltiplos candidatos com distância (aditivo) | python | 00 | done | task/04 — integrado | |
| 05 | Prompts (base + injections) + montagem | python | 00 | done | task/05 — integrado | |
| 06 | Classificador (LLM → Intencao) | python | 01,03,05 | done | task/06 — integrado | |
| 07 | RAG (busca 3 faixas) | python | 03,04 | done | task/07 — integrado | |
| 08 | Tool Cadastrar + helpers de parcelas | python | 01,02,03,05 | done | task/08 — integrado | |
| 09 | Tool Listar | python | 01,03,04 | done | task/09 — integrado | |
| 10 | Tools Atualizar e Excluir | python | 01,02,03,07 | done | task/10 — integrado | |
| 11 | Tool Conversar | python | 01,05 | done | task/11 — integrado | |
| 12 | Formatador (templates Python) | python | 01 | done | task/12 — integrado | |
| 13 | Roteador (match + guarda de pendência) | python | 06,08,09,10,11,12 | todo | — | |
| 14 | Webhook + Worker (auth, dedup, fila, debounce) | python | 02,13 | todo | — | |
| 15 | Evolution client robusto | python | 00 | done | task/15 — integrado | |
| 16 | Integração (wiring) + limpeza dos módulos antigos | python | 13,14,15 | todo | — | |

## Ondas de paralelismo

- Onda 1 (após 00): 01, 02, 03, 04, 05, 15
- Onda 2: 06, 07, 08, 09, 10, 11, 12
- Onda 3: 13
- Onda 4: 14
- Onda 5: 16 (serial)
