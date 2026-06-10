# Plan: Melhorias de Negócio — Parcelas, Status, Receitas e Projeção

**Status:** Aprovado
**Feature:** melhorias-dashboard
**Spec:** specs/melhorias-dashboard/spec.md
**Exploração:** specs/melhorias-dashboard/exploracao.md

---

## Arquitetura

Evolução incremental nas três camadas existentes — sem componentes novos além de um
service puro (`parcelas.py`), um blueprint (`api_projecao.py`), um service de
confirmação (`marcar_pago.py`) e um script CLI (`backfill_parcelas.py`).

### Decisões técnicas

| # | Decisão | Alternativa descartada | Motivo |
|---|---------|----------------------|--------|
| 1 | Helper puro `app/services/parcelas.py` (adicionar_meses/clamp, datas_do_grupo, status_por_data) | dateutil; lógica duplicada em Cadastrar e backfill | Projeto não usa dateutil; T03 e T10 compartilham a mesma regra por contrato |
| 2 | Colunas String + `server_default` na migration | Enum nativo do Postgres | Padrão atual do projeto (tipo/categoria já são String) |
| 3 | `MarcarPagoService` novo espelhando `AlterarService` | Estender AlterarService | Anti-colisão: T04 não toca arquivo do fluxo ALTERAR; estados separados |
| 4 | Categoria PARCELAMENTOS/RECEITA forçada no service | Ensinar o categorizador LLM | Determinístico, sem custo de LLM, regra de negócio fixa |
| 5 | Projeção em blueprint próprio (`api_projecao.py`) | Dentro de api_graficos | api_graficos não muda; tarefa isolada |
| 6 | Projeção renderizada por app.js como tabela compacta | Canvas em charts.js | charts.js intocado; menos colisão e menos JS |
| 7 | Extração diferencia `valor_por_parcela` × `valor_total` | Sempre dividir total | RN-01: "R$200 parcela 2/4" = 200/parcela (campo já existia no modelo) |
| 8 | Backfill com funções puras + repository mockado nos testes | Teste de integração com DB | Padrão do projeto: zero DB real em testes |
| 9 | `detalhes` fora do embedding | Reembeddar com detalhes | Spec: formato do embedding inalterado; busca semântica preservada |

---

## Tabela de Tarefas

| ID | Tarefa | Stack | Deps | Arquivos próprios (resumo) |
|----|--------|-------|------|---------------------------|
| 01 | Modelo de dados, migration, helper parcelas | python | — | enums, transacao, dtos, repository, migration 0002, parcelas.py, test_repository, test_parcelas_helper |
| 02 | Extração v2 | python | 01 | extrator.py, prompts/sistema.md, test_agents.py |
| 03 | Cadastrar v2 (1..N, status, receitas) | python | 01, 02 | cadastrar.py, prompts/categorizacao.md, test_service_cadastrar.py |
| 04 | Marcar pago via WhatsApp | python | 01 | classificador.py, prompts/intencao.md, marcar_pago.py, pipeline.py, main.py, test_pipeline.py, test_marcar_pago.py |
| 05 | Consultar/Formatador com receitas | python | 01 | consultar.py, formatador.py, prompts/resumo.md, test_service_consultar.py |
| 06 | API resumo v2 + projeção | python | 01 | api_resumo.py, api_projecao.py, dashboard/app.py, test_dashboard_resumo.py, test_dashboard_projecao.py |
| 07 | API transações v2 | python | 01 | api_transacoes.py, test_dashboard_transacoes.py |
| 08 | Front base (templates, cards, projeção) | python+js | 01 | index.html, app.js, test_dashboard_templates.py |
| 09 | Front tabela (badges, filtro, modais) | js | 07, 08 | table.js |
| 10 | Backfill de parcelas | python | 01 | scripts/backfill_parcelas.py, tests/test_backfill.py |

---

## DAG

```
            ┌──► T02 ──► T03
            ├──► T04
            ├──► T05
T01 ────────┼──► T06
            ├──► T07 ──┐
            ├──► T08 ──┴──► T09
            └──► T10
```

- **Lote 1:** T01 (fundação)
- **Lote 2:** T02, T04, T05, T06, T07, T08, T10 (paralelo — sem arquivos em comum)
- **Lote 3:** T03 (após T02), T09 (após T07+T08) — paralelo entre si

---

## Contratos

| Contrato | Arquivo | Status |
|----------|---------|--------|
| Modelo de Dados v2 | `contracts/modelo-dados.md` | Congelado |
| Extração v2 | `contracts/extracao-v2.md` | Congelado |
| API JSON v2 | `contracts/api-json-v2.md` | Congelado |
| DOM v2 | `contracts/dom-v2.md` | Congelado |

---

## Ordem de integração

1. T01 → rodar suíte completa (nada deve quebrar: campos têm defaults)
2. T02, T04, T05, T06, T07, T08, T10 em qualquer ordem
3. T03 e T09
4. `uv run alembic upgrade head` no banco real → `scripts/backfill_parcelas.py --dry-run` → revisar relatório → rodar de verdade
5. Smoke manual no browser (cenários "manual" de 08/09)

---

## Riscos

| Risco | Prob. | Mitigação |
|-------|-------|-----------|
| Testes existentes assumem saldo = invest − gastos e serialização sem campos novos | Alta | T06/T07 são donos dos arquivos de teste e os ajustam à nova semântica (sem deletar cenários) |
| Backfill em dados reais com grupos sujos | Média | `--dry-run` obrigatório no passo de integração; ambíguos nunca tocados |
| Extração LLM errar parcela atual vs total | Média | Exemplos explícitos no prompt + defaults seguros (atual=1 = comportamento antigo) |
| `filtro-tipo` no template não exibir RECEITA | Baixa | `dashboard/app.py` deriva de `TipoEnum` dinamicamente (conferido na exploração); T08 testa |

---

## Verificação da feature completa

```bash
uv run pytest tests/ -q                 # tudo verde
uv run alembic upgrade head             # migration ok
uv run python scripts/backfill_parcelas.py --dry-run
uv run flask --app dashboard.app run --port 5000   # smoke manual RF-06/07/09
```

| RF | Check |
|----|-------|
| RF-01 | upgrade + downgrade verdes; antigos data<hoje = PAGO |
| RF-02 | WhatsApp "parcela 2/4" → 4 linhas no banco, dia preservado |
| RF-03 | PIX→PAGO; "paguei X"→confirmação→PAGO; PUT status no painel |
| RF-04 | responsavel capturado; coluna no painel |
| RF-05 | detalhes preenchido/NULL; tooltip no painel |
| RF-06 | card Receitas; saldo = receitas−gastos; balanço no WhatsApp |
| RF-07 | projeção 6 meses só PENDENTEs |
| RF-08 | backfill idempotente com relatório |
| RF-09 | badges, filtro status, modais v2 |
