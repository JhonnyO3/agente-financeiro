# Tarefa 02 — Atualizar prompt `02-extracao-cadastrar.md`

**Stack:** python  
**Estado:** todo  
**Depende de:** nenhuma  
**Bloqueia:** nenhuma (independente, mas 01 a usa)

## Objetivo

Reescrever `agent/prompts/02-extracao-cadastrar.md` para:

1. **RF-02**: Adicionar seção "## Uso do histórico" instruindo explicitamente o LLM a consultar `{historico_recente}` para resolver ambiguidades de `forma_pagamento`, `dia_vencimento` e `parcelas`.
2. **RF-03**: Remover qualquer lista de plataformas/apps (Mercado Pago, iFood, etc.). Substituir por regras baseadas em intenção de pagamento do usuário.

## Arquivos que esta tarefa possui

- `agent/prompts/02-extracao-cadastrar.md` ← reescrever

## NÃO toca em

- Nenhum arquivo Python

## Mudanças no prompt

### Seção nova: "## Uso do histórico" (inserir após "## Parâmetros recebidos")

```markdown
## Uso do histórico

O campo `{historico_recente}` contém as mensagens anteriores desta conversa.

**Regra:** se `forma_pagamento`, `dia_vencimento` ou `parcelas` foram mencionados em mensagens anteriores, use esses valores — não peça de novo.

Exemplos de extração cross-turno:
- Turno 1: "comprei roupa" (sem forma) → Turno 2: "foi no crédito" → `forma_pagamento=CARTAO_CREDITO` com base no histórico
- Turno 1: "gastei 300" → Turno 2: "em 3x" → `total_parcelas=3, parcela_atual=1`
```

### Seção "Forma de pagamento" — tornar agnóstica

Substituir regras de plataforma por regras de intenção:

```markdown
## Regras de extração — Forma de pagamento

Inferir a forma com base no que o usuário comunicou sobre a transação:

- Menção a parcelas, "em Nx", "no crédito", vencimento futuro ("vence dia X") → `CARTAO_CREDITO`
- "pix", "transferência", "à vista no débito", "cartão de débito" → `PIX` / `CARTAO_DEBITO`
- "no boleto" → `BOLETO`
- "dinheiro" → será mapeado para PIX pela Tool
- Nenhum contexto claro de forma → `forma_pagamento=null` (campo faltante, será perguntado)

> Não faça mapeamento por nome de app ou banco. Interprete o sinal de pagamento que o usuário comunicou.
```

## Critério de verificação local

```bash
uv run pytest tests/test_prompts.py -v -k "extracao"
```

- Verificar que o prompt renderizado contém a seção de uso do histórico.
- Verificar que o prompt não contém nomes de plataformas hardcodadas.
