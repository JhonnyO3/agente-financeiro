# Tarefa 10 — Script de backfill de parcelas

**Stack:** python · **Dependências:** 01
**Contratos:** `contracts/modelo-dados.md`

## Arquivos que esta tarefa possui
- `scripts/backfill_parcelas.py` (novo) · `scripts/__init__.py` (se necessário)
- `tests/test_backfill.py` (novo)

## O que implementar
Script CLI (`uv run python scripts/backfill_parcelas.py [--dry-run]`), sessão via
`app.repositories.database` + `app.config`:
1. Buscar grupos com `parcela_total > 1`; para cada um, comparar nº de registros com
   `parcela_total`
2. Grupo incompleto e CONSISTENTE (mesmo valor, descricao, parcela_total em todos):
   criar as parcelas faltantes — data derivada com `datas_do_grupo`/`adicionar_meses`
   a partir de uma parcela existente, `status = status_por_data`, demais campos
   copiados do grupo (incluindo embedding e categoria)
3. Grupo AMBÍGUO (valores/descrições divergentes, parcela_numero duplicado, ou
   parcela_numero > parcela_total) → pular e listar no relatório com o motivo
4. Relatório final: grupos completados, parcelas criadas, grupos pulados (motivo)
5. `--dry-run`: relatório sem gravar. Idempotente: rodar de novo → 0 criações
6. Lógica de decisão (separar faltantes/ambíguos) em funções puras testáveis sem DB;
   testes mockam o repository

## Critérios de aceite
- [ ] Grupo 2/4 com só a parcela 2 → cria 1 (PAGO se passada), 3 e 4 (PENDENTE)
- [ ] Segunda execução não cria nada
- [ ] `--dry-run` não chama `criar_lote`
- [ ] Grupo com valores divergentes → intacto + motivo no relatório

## Verificação
`uv run pytest tests/test_backfill.py -v` e suíte completa verde.
