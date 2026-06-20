# Plano — Contexto Multi-turno, Extração em 2 Etapas e Harness de Testes

**Status: Aprovado**  
Feature: `agent-contexto-e-testes`  
Data: 2026-06-20

---

## Diagnóstico confirmado

A exploração confirmou o problema central: `montar_prompt("cadastrar", ctx)` existe e funciona, mas **nenhum código de produção a chama**. O único chamador de `montar_prompt` é `Classificador.classificar`, que usa apenas `"classificador"`. As regras de extração de `02-extracao-cadastrar.md` são letra morta.

---

## Arquitetura das mudanças

```
[Mensagem] → Classificador (etapa 1 — ação + parâmetros parciais)
                ↓
           Roteador.rotear
                ↓ (se acao == "cadastrar")
           Extrator.extrair_cadastro (etapa 2 — LLM com 02-extracao-cadastrar.md)
                ↓
           ToolCadastrar.executar (valida, pede campos faltantes, monta registros)
```

### Novos componentes

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| `Extrator` | `agent/services/extrator.py` | 2ª chamada LLM para preencher ItemCadastro |
| `HarnessAgente` | `scripts/chat_terminal.py` | Pipeline CLI sem WhatsApp |
| `cenarios_teste.jsonl` | `scripts/cenarios_teste.jsonl` | 60 cenários de teste |

### Componentes modificados

| Componente | Arquivo | Mudança |
|---|---|---|
| `Roteador` | `agent/services/roteador.py` | Injetar e chamar `Extrator` |
| `main.py` | `agent/entrypoint/main.py` | Criar e injetar `Extrator` |
| `ToolCadastrar` | `agent/tools/cadastrar.py` | Checar `forma_pagamento` nos campos faltantes |
| `02-extracao-cadastrar.md` | `agent/prompts/02-extracao-cadastrar.md` | Adicionar instrução de histórico; remover plataformas hardcodadas |

---

## Tabela de tarefas (DAG)

| ID | Tarefa | Stack | Depende de | Paralela com |
|----|--------|-------|------------|--------------|
| 01 | Criar `Extrator` (segunda etapa LLM) | python | — | 02, 04, 05 |
| 02 | Atualizar prompt `02-extracao-cadastrar.md` | python | — | 01, 04, 05 |
| 03 | Wiring: Extrator no Roteador + main.py | python | 01 | 04, 05 |
| 04 | ToolCadastrar: pedir `forma_pagamento` | python | — | 01, 02, 05 |
| 05 | Harness CLI (`chat_terminal.py`) | python | — | 01, 02, 04 |
| 06 | Suite de 60 cenários (`.jsonl`) | python | 05 | — |
| 07 | Smoke tests mínimos (3 + 2 casos) | python | 01, 03, 04 | 06 |

**Ondas de execução:**

- **Onda 1 (paralela):** 01, 02, 04, 05
- **Onda 2 (paralela):** 03 (depende 01), 06 (depende 05)
- **Onda 3:** 07 (depende 01, 03, 04)

---

## Decisões de arquitetura

1. **`Extrator` como serviço injetável**: permite mock em testes sem tocar no Roteador. Parâmetro opcional (`extrator=None`) garante retrocompatibilidade total.

2. **Mesclagem de campos**: o Extrator **não sobrescreve** campos já preenchidos pelo Classificador — só preenche `None`. Garante que a extração parcial do classificador sempre vence.

3. **Prompt agnóstico a plataformas (RF-03)**: o prompt instrui o LLM a interpretar sinais de intenção (`"vence dia X"`, `"em Nx"`, `"no crédito"`) em vez de nomear apps. Mais robusto a novos serviços de pagamento.

4. **`forma_pagamento` como campo faltante**: só perguntar quando não há pista alguma de parcelamento ou vencimento. Evita perguntas desnecessárias no caminho feliz.

5. **Harness com RepoMock**: sem banco real. Suficiente para testar o pipeline de classificação + extração + formatação. Persistência não é o foco desta feature.

6. **`--seed` via monkey-patch de LLM**: `_SeedLLM` substitui `ChatOpenAI` inteiramente — zero chamadas reais. Simples, sem dependência de framework de mock.

---

## Riscos

| Risco | Mitigação |
|---|---|
| Segunda chamada LLM aumenta latência | Aceito — sem timeout SLA definido na spec |
| LLM não-determinístico pode falhar cenários | Margem de 5/60 (RF-06); `--seed` para CI |
| `montar_prompt("cadastrar")` exige `{parametros}` — novo campo | Adicionado no `Extrator`; não quebra chamada atual do `Classificador` |
| Testes existentes do Roteador mockam sem `extrator` | Parâmetro opcional — testes existentes não precisam mudar |

---

## Ordem de integração

1. Tarefas 01 + 02 + 04 + 05 (paralelas, sem dependências cruzadas)
2. Tarefa 03 (integra 01 no Roteador)
3. Tarefa 06 (usa 05 para validar)
4. Tarefa 07 (testa tudo junto)
5. Rodar `uv run pytest tests/ -v` — suite completa verde
6. Rodar `uv run python scripts/chat_terminal.py --batch scripts/cenarios_teste.jsonl` — verificar ≥55/60

---

## Verificação da feature

```bash
# Suite de testes (sem LLM):
uv run pytest tests/ -v

# Harness interativo (com LLM real):
uv run python scripts/chat_terminal.py

# Batch completo (com LLM real):
uv run python scripts/chat_terminal.py --batch scripts/cenarios_teste.jsonl

# CI sem custo (com seed):
uv run python scripts/chat_terminal.py --batch scripts/cenarios_teste.jsonl --seed scripts/seed_respostas.json
```
