# Tarefa 05 — Refatorar `Formatador` para usar templates

**Stack:** python
**Depende de:** 04 (loader + templates disponíveis)
**Contrato:** `contracts/template-loader.md`

## Objetivo

Mover o layout de resposta de `agent/services/formatador.py` para os templates externos. O Formatador
passa a **montar contexto** (formatação `_fmt`, emojis, agrupamento, diff) em Python e delegar o
desenho a `template_loader.renderizar`, **sem strings de resposta hardcoded** e **sem regressão** de
output.

## Arquivos (posse exclusiva)

- `agent/services/formatador.py`

## Escopo

1. Manter `Formatador.formatar(resultado: ResultadoTool) -> str` síncrono e o `match (acao, status)`.
2. Cada branch monta um `contexto: dict` (com chaves `_fmt`, emojis, listas) e chama
   `renderizar("<template>.md", contexto)`. Manter `_brl`, `_status_emoji`, `_card_registro`
   (ou seu equivalente como contexto) e demais cálculos em Python.
3. `conversar/concluido` permanece passthrough (`dados["resposta"]`), sem template.
4. Remover as strings de layout hardcoded dos branches/helpers (📊, 📭, menu, cards, etc.).
5. Garantir equivalência byte a byte com o output atual.

## Critérios de aceite → teste

- [ ] `tests/test_formatador.py` continua **verde sem alterar os testes** (output equivalente)
- [ ] `grep -n '"📊' agent/services/formatador.py` → 0 (sem o cabeçalho de listar hardcoded)
- [ ] `grep -n 'Confirme o registro' agent/services/formatador.py` → 0 (texto migrou para template)
- [ ] `_brl` e cálculo de emoji permanecem em Python
- [ ] Alterar texto em `listar_concluido.md` muda o output sem tocar Python (validado por teste do loader/T04)
- [ ] Sem chamadas a LLM; `formatar` continua síncrono

## Verificação local

```bash
uv run pytest tests/test_formatador.py -v
```
