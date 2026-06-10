# Tarefa 05 — Migração de sanitização dos dados existentes (0004)

**Stack:** python
**Depende de:** 01
**Contratos:** `contracts/enums.md`, `contracts/schema-transacoes.md`
**Alvo de dados:** `specs/melhorias-cadastramento/dados-corrigidos.txt`

## Objetivo

Migrar os registros existentes para o estado sanitizado (RF-08), de forma idempotente.

## Arquivos (posse exclusiva)

- `migrations/versions/0004_sanitizacao_dados.py` (novo, `down_revision='0003'`)

## Escopo (UPDATE/DELETE/INSERT via `op.execute`)

1. **Forma:** `CARTAO` → `CARTAO_CREDITO`. Todo `OUTRO` remanescente: `parcela_total > 1` ou
   recorrente/assinatura → `CARTAO_CREDITO`; à vista → `PIX`. Nenhum `OUTRO` pode sobrar.
2. **Recategorização:**
   - asimov academy, curso claude code, curso de inglês → `EDUCACAO` (tipo `GASTO`)
   - jogo batman, pandora do Morumbi, parcela do carro, parcela do celular, Nubank → `COMPRAS`
   - parcela do aquecedor → `GASTOS_PONTUAIS` (tipo `GASTO`)
3. **Recorrentes:** academia, LinkedIn, Spotify → `recorrente=TRUE`, `parcela_numero=parcela_total=1`.
   Spotify (assinatura) → `CARTAO_CREDITO`; `uber` (à vista) → `PIX`.
4. **Valores corrigidos:** aquecedor 633, celular 228, cuecas 174, carro 1200, Nubank 922,
   batman 74,90/74,91/74,92/74,93.
5. **Remover (DELETE):** Coxinha, Sorvete do Mac, tokens open ai, Claude code (472, OUTROS).
6. **Inserir recorrentes:** Google Drive (14,90), Claude code Max (500) — `GASTOS_FIXOS`,
   `recorrente=TRUE`, sem parcela.
7. **`zara`:** gerar `grupo_parcela_id` (UUID) próprio, desvinculando do grupo do batman.
8. Sem categoria `PARCELAMENTOS`/`OUTROS` ao final.

## Critérios de aceite

- [ ] `SELECT count(*) WHERE forma_pagamento='OUTRO'` = 0
- [ ] `SELECT count(*) WHERE categoria IN ('PARCELAMENTOS','OUTROS')` = 0
- [ ] academia, LinkedIn, Spotify, Google Drive, Claude code Max: `recorrente=TRUE`, sem parcela
- [ ] 4 itens de teste removidos; `zara` com grupo próprio
- [ ] Idempotente: rodar `upgrade` 2x não duplica nem corrompe
- [ ] `downgrade` documentado (irreversível em dados → registrar no docstring)

## Verificação local

```bash
uv run alembic upgrade head
# validar invariantes em banco de fixture
```
