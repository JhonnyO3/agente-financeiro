# Tarefa 05 — start.py unificado e remoção do dashboard antigo

**Stack:** python
**Depende de:** 01, 02, 03, 04
**Contratos:** `frontend-backend.md`

## Objetivo

Script único que sobe backend (:8000) e frontend (:5000) juntos, e remoção do `dashboard/` antigo
(substituído) e dos testes que o miravam.

## Arquivos (posse exclusiva)

- `start.py` (raiz)
- Remoção: `dashboard/**`, `tests/test_dashboard_*.py`

## Escopo

1. `start.py`: sobe via `subprocess` `uvicorn backend.main:app --port 8000` e
   `flask --app frontend.app run --port 5000` (ou equivalente). Logs dos dois no mesmo terminal
   com prefixo `[backend]`/`[frontend]`. `CTRL+C` encerra ambos sem órfãos
   (Windows: `CREATE_NEW_PROCESS_GROUP` + `terminate()`; POSIX: `SIGINT`).
2. Conferir **paridade**: todas as rotas do `dashboard/` antigo existem no backend+frontend.
3. Remover `dashboard/**` e `tests/test_dashboard_*.py` (substituídos por `tests/backend` e
   `tests/frontend`). Atualizar `README.md`/comandos se citarem `dashboard.app`.

## Critérios de aceite

- [ ] `uv run python start.py` sobe os dois serviços nas portas indicadas
- [ ] Logs prefixados por origem; `CTRL+C` encerra ambos sem processo órfão
- [ ] `dashboard/` e `tests/test_dashboard_*` removidos; `uv run pytest` verde
- [ ] Nenhuma referência pendente a `dashboard.app` no repo

## Verificação local

```bash
uv run pytest -q
uv run python start.py   # smoke manual: dois serviços + CTRL+C limpo
```
