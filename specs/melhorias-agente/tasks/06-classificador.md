# Tarefa 06 — Classificador (LLM → Intencao)

**Stack:** python
**Depende de:** 01, 03, 05
**Contrato:** `intencao-schema.md`, `prompts-injection.md`

## Objetivo
Chamada LLM única de roteamento: mensagem + histórico + estado_pendente → `Intencao` tipada.

## Arquivos (posse exclusiva)
- `agent/services/classificador.py`
- `tests/test_classificador.py`

## Escopo
1. `Classificador.classificar(mensagem, historico, estado_pendente) -> Intencao` via `criar_llm(Settings.LLM_MODELO_CLASSIFICACAO).with_structured_output(Intencao)`.
2. Monta prompt via `montar_prompt("classificador", ctx)`.
3. `confianca < Settings.CONFIANCA_MINIMA` → `acao="desconhecida"`.
4. Aplica as regras de pendência do contrato (delegadas ao prompt; o serviço só repassa contexto).

## Critérios de aceite
- [ ] Mock de LLM devolvendo cada exemplo de `classificador.md` produz a `Intencao` esperada.
- [ ] `confianca` baixa vira `desconhecida`.
- [ ] Recebe e injeta `historico` e `estado_pendente`.

## Verificação
```bash
uv run pytest tests/test_classificador.py -v
```
