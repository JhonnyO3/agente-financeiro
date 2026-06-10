# Tarefa 07 — API transações v2 (novos campos e filtro status)

**Stack:** python · **Dependências:** 01
**Contratos:** `contracts/api-json-v2.md`, `contracts/modelo-dados.md`

## Arquivos que esta tarefa possui
- `dashboard/blueprints/api_transacoes.py` · `tests/test_dashboard_transacoes.py`

## O que implementar
1. Serializador: + `status`, `forma_pagamento`, `responsavel`, `detalhes` (null → `""`)
2. GET: novo query param `status` (PAGO/PENDENTE), combinável com os existentes
3. POST: aceita os 4 campos opcionais com defaults do contrato; valores fora dos
   enums → 400. Receita manual sem status → PAGO se data ≤ hoje (regra do modelo)
4. PUT: aceita os 4 campos (parciais) no `TransacaoUpdate`

## Critérios de aceite
- [ ] GET serializa os 4 campos; filtro `status=PENDENTE` combina com tipo/categoria
- [ ] POST com `forma_pagamento=PIX` → status PAGO; inválido → 400
- [ ] PUT só com `{"status": "PAGO"}` gera `TransacaoUpdate(status=PAGO)` e nada mais
- [ ] Testes existentes ajustados (serialização ganhou campos), não deletados

## Verificação
`uv run pytest tests/test_dashboard_transacoes.py -v` e suíte completa verde.
