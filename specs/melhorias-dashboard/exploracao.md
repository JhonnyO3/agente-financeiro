# Exploração — melhorias-dashboard

## Estado atual relevante

| Área | Arquivo | O que importa para esta feature |
|---|---|---|
| Modelo | `app/models/transacao.py` | 11 colunas; SEM status/forma_pagamento/responsavel/detalhes |
| Enums | `app/models/enums.py` | `TipoEnum`: GASTO, INVESTIMENTO. `CategoriaEnum`: 8 valores (OUTROS já existe; faltam RECEITA, PARCELAMENTOS) |
| DTOs | `app/repositories/dtos.py` | `TransacaoCreate` (9 campos, `grupo_parcela_id: UUID`), `TransacaoUpdate` (5 opcionais), `AgregadoCategoria` |
| Repository | `app/repositories/transacao_repository.py` | `criar`/`criar_lote` montam `Transacao(...)` campo a campo — precisam dos novos campos. `atualizar` usa `asdict` genérico (novos campos no DTO bastam) |
| Migrations | `migrations/versions/0001_create_transacoes_table.py` | única migration; a nova será 0002 |
| Extrator | `app/agents/extrator.py` | `ExtracaoResult` JÁ tem `valor_por_parcela: Decimal\|None` e `parcela_total`; faltam `parcela_atual`, `forma_pagamento`, `responsavel`, `detalhes`, tipo RECEITA. Prompt: `prompts/sistema.md` |
| Classificador | `app/agents/classificador.py` | `IntencaoResult.intencao` é `Literal[...7 valores]`; prompt `prompts/intencao.md` |
| Cadastrar | `app/services/cadastrar.py` | `_processar` gera parcelas com `data_base + timedelta(days=30*i)` a partir da parcela 1 — substituir por dia preservado e geração 1..N com parcela_atual |
| Alterar | `app/services/alterar.py` | Padrão pronto para "marcar pago": embedder + `buscar_semantico_com_distancia` (>1.0 = não achou) + `EstadoConfirmacao` + confirmar(sim/não) |
| Consultar | `app/services/consultar.py` | Totais separam investimento por CATEGORIA (não tipo); receitas terão categoria RECEITA → `agregar_por_categoria` continua servindo |
| Pipeline | `app/services/pipeline.py` | Roteia por `intencao.intencao` e por `estado.acao` (strings livres — novo estado MARCAR_PAGO não exige enum) |
| Wiring | `app/entrypoint/main.py` | Lifespan instancia tudo; novo service de marcar-pago entra aqui |
| Dashboard API | `dashboard/blueprints/api_resumo.py`, `api_transacoes.py` | resumo: saldo = investimentos − gastos (vai mudar); transacoes: serializador explícito (novos campos) |
| Dashboard app | `dashboard/app.py` | Registro dinâmico itera tupla hardcoded de 4 nomes — adicionar `api_projecao` exige editar este arquivo |
| Dashboard front | `templates/index.html`, `static/app.js`, `static/table.js` | ids congelados em `specs/dashboard-flask/contracts/js-interop.md`; modais com campos `edit-*`/`add-*` |
| Prompts | `prompts/` | sistema.md (extrator), intencao.md, categorizacao.md, resumo.md, confirmacao.md, cadastro-confirmado.md, fora-de-escopo.md |
| Testes | `tests/` | 13 arquivos, todos mockados. `test_agents.py` (extrator), `test_service_cadastrar.py`, `test_service_consultar.py`, `test_pipeline.py`, `test_dashboard_*.py` |

## Reuso e riscos

- **Aritmética de meses**: não há dateutil no projeto — helper manual `adicionar_meses` com clamp p/ último dia do mês (novo `app/services/parcelas.py`, compartilhado por Cadastrar e backfill).
- **Colisão de testes**: `test_agents.py` cobre extrator E classificador → dono único (T02); mudanças do classificador são testadas via `test_pipeline.py` (T04).
- **`atualizar` genérico**: basta adicionar campos ao `TransacaoUpdate`; nenhum método novo de repository é necessário.
- **Projeção**: `listar_por_periodo(hoje, fim_6_meses)` + agregação Python — padrão já usado no dashboard.
- **Backfill toca banco real**: script fora do app (`scripts/`), com `--dry-run`, sessão própria via `app.repositories.database`.
- **Embedding inalterado**: `gerar_para_transacao(tipo, categoria, descricao, data)` não recebe os novos campos — conferido, nenhum chamador precisa mudar além dos existentes.
