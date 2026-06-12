# Tarefa 03 — Relógio injetável + novas Settings

**Stack:** python
**Depende de:** 00
**Contrato:** `relogio-contexto.md`

## Objetivo
`Relogio` com TZ do usuário e as novas Settings da feature.

## Arquivos (posse exclusiva)
- `agent/services/relogio.py`
- `agent/config.py`
- `tests/test_relogio_config.py`

## Escopo
1. `relogio.py`: `Relogio(tz).agora()/hoje()` aware no fuso do usuário.
2. `config.py`: adicionar `RESPONSAVEL_PADRAO`, `TIMEZONE_USUARIO`, `WEBHOOK_APIKEY`, `REDIS_URL`, `DEBOUNCE_SEGUNDOS`, `CONFIANCA_MINIMA`, `RAG_PISO`, `RAG_MARGEM`, `RAG_MAX_OPCOES`, `LLM_MODELO_CLASSIFICACAO`, `LLM_MODELO_CONVERSAR`. Remover default de `AGENTE_USUARIO_EMAIL`. Documentar invariante "1 worker" (fila/debounce in-process).
3. `RESPONSAVEL_PADRAO`/`WEBHOOK_APIKEY`/`AGENTE_USUARIO_EMAIL`/`REDIS_URL` sem default (obrigatórios).

## Critérios de aceite
- [ ] `Relogio("America/Sao_Paulo").hoje()` corrige a virada de dia em UTC (teste com relógio fixo).
- [ ] Settings sem os obrigatórios falham explicitamente.

## Verificação
```bash
uv run pytest tests/test_relogio_config.py -v
```
