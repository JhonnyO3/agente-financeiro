# Plano Técnico — melhorias-cadastramento

**Status:** APROVADO
**Spec:** `specs/melhorias-cadastramento/spec.md` (Aprovada)
**Contratos:** `contracts/enums.md` (Congelado), `contracts/schema-transacoes.md` (Congelado)

## Arquitetura da mudança

Quatro frentes a partir de uma base comum:

1. **Base (T01):** enums + coluna `recorrente` + DTOs + migration de schema (0003). É a fonte
   dos dois contratos congelados; tudo depende dela.
2. **Agente/cadastro (T02):** regras de forma de pagamento, status/data por forma, fim do
   `PARCELAMENTOS`, valor por parcela e o novo fluxo de confirmação de recorrência.
3. **Categorização/prompts (T03):** Literal de categorias (+EDUCACAO, −OUTROS) e prompts.
4. **Dashboard (T04):** selects e cores refletem os novos enums.
5. **Migração de dados (T05):** sanitização dos registros existentes (0004).

## Decisões

- **Data de fatura** = `adicionar_meses(data, 1)` (mesmo dia, mês seguinte). Reusa função pura
  existente em `parcelas.py`. Sem dia de fechamento configurável.
- **Recorrência** via flag booleano `recorrente`, não tabela separada. `data` continua NOT NULL.
- **Enum como contrato congelado** antes de paralelizar T02–T05, evitando quebra de espelhamento.
- **Migração de dados separada da migração de schema** (0004 depende de 0003) para manter cada
  migration com responsabilidade única e `downgrade` limpo.
- **Anti-colisão por arquivo:** T02 (serviços/agente extrator) e T03 (categorizador+prompts) e
  T04 (dashboard) e T05 (migration 0004) não compartilham arquivos.

## Tarefas (DAG)

| ID | Tarefa | Stack | Depende de | Arquivos (posse) |
|----|--------|-------|-----------|------------------|
| 01 | Enums, coluna `recorrente`, DTOs, migration 0003 | python | — | `app/models/enums.py`, `app/models/transacao.py`, `app/repositories/dtos.py`, `migrations/versions/0003_*.py` |
| 02 | Regras de pagamento, status/data, fim do PARCELAMENTOS, fluxo recorrência | python | 01 | `app/services/cadastrar.py`, `app/services/parcelas.py`, `app/services/confirmacao_state.py`, `app/services/pipeline.py`, `app/agents/extrator.py` |
| 03 | Categorizador + prompts refletem novos enums | python | 01 | `app/agents/categorizador.py`, `prompts/categorizacao.md`, `prompts/sistema.md` |
| 04 | Dashboard reflete novos enums | python | 01 | `dashboard/templates/index.html`, `dashboard/static/charts.js`, `dashboard/blueprints/api_transacoes.py` |
| 05 | Migração de sanitização dos dados (0004) | python | 01 | `migrations/versions/0004_*.py` |

T02, T03, T04, T05 rodam em paralelo após T01.

## Ordem de integração

1. T01 (merge primeiro — congela contratos no código).
2. T02, T03, T04, T05 em qualquer ordem (sem colisão de arquivos).
3. Rodar suíte completa + `alembic upgrade head` em banco com dados de fixture.

## Riscos

- **Default `OUTRO` órfão:** se T01 mudar o enum mas a 0004 (T05) não rodar, dados antigos com
  `OUTRO`/`PARCELAMENTOS` ficam inválidos para o ORM. Mitigação: T05 obrigatória antes de subir.
- **Espelhamento de Literal:** T02/T03 precisam bater 1:1 com `contracts/enums.md`. QA cobre via
  cenários de cadastro.
- **Embeddings dos migrados:** categoria muda mas embedding não é refeito (fora de escopo) — busca
  semântica dos itens recategorizados pode degradar levemente; aceito nesta entrega.

## Verificação da feature

- `uv run pytest tests/ -v` verde.
- `uv run alembic upgrade head && uv run alembic downgrade -2` sem erro (0003+0004 reversíveis).
- Invariantes pós-migração (RF-08): nenhum `OUTRO`/`PARCELAMENTOS`/`OUTROS`; recorrentes sem parcela.
- Cenários Gherkin em `scenarios/` cobrindo RF-02/03/05/06/08.
