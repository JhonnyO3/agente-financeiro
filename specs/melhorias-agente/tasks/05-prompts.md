# Tarefa 05 — Prompts (base + injections) + montagem

**Stack:** python
**Depende de:** 00
**Contrato:** `prompts-injection.md`

## Objetivo
Reorganizar prompts para o sistema base+injection (só chamadas LLM reais) e a função de montagem.

## Arquivos (posse exclusiva)
- `agent/prompts/00-base.md`
- `agent/prompts/01-classificador.md`
- `agent/prompts/02-extracao-cadastrar.md`
- `agent/prompts/03-extracao-atualizar.md`
- `agent/prompts/06-conversar.md`
- `agent/services/prompts.py`
- `agent/agents_llm.py`  # ex-agents/base.py: carregar_prompt, coagir_data, criar_llm via Settings, Embedder reexport
- `tests/test_prompts.py`

## Escopo
1. `00-base.md` conforme `prompt-base.md` (variáveis: user_name, data_atual, responsavel_padrao, historico_recente, estado_pendente, injection_acao).
2. `01-classificador.md` derivado de `classificador.md` (10 intenções, regras de pendência, exemplos; remover blocos "```json" redundantes com structured output).
3. `02-extracao-cadastrar.md` (extração rica + categorização absorvida), `03-extracao-atualizar.md`, `06-conversar.md` (diálogo puro, sem banco).
4. `agents_llm.py`: mover `carregar_prompt`/`coagir_data`/`criar_llm*` de `agents/base.py`, com modelos vindos de `Settings`.
5. `prompts.py`: `montar_prompt(acao, contexto)` conforme contrato; falha explícita em variável faltante.

## Critérios de aceite
- [ ] `montar_prompt("classificador", ctx)` injeta o arquivo certo e preenche tudo sem KeyError.
- [ ] `{responsavel_padrao}` vem de Settings.
- [ ] Só existem prompts para classificador/cadastrar/atualizar/conversar.

## Verificação
```bash
uv run pytest tests/test_prompts.py -v
```
