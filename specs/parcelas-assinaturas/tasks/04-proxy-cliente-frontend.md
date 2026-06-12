# Tarefa 04 — Proxy Flask e cliente HTTP para os endpoints novos

**Stack:** python
**Depende de:** 02, 03
**Contratos:** `contracts/frontend-dashboard.md`, `contracts/api-grupos.md`, `contracts/api-gastos-fixos.md`

## Objetivo

Expor via Flask todos os endpoints novos do backend (RF-05): métodos no `BackendClient` e
rotas no `api_proxy`, seguindo o padrão existente (repasse de status/corpo; 502 quando o
backend cai).

## Arquivos (posse exclusiva)

- `frontend/services/backend_client.py`
- `frontend/blueprints/api_proxy.py`
- `tests/frontend/test_proxy_parcelas_assinaturas.py` (novo)

## Escopo

1. **`BackendClient`:** `atualizar_grupo(grupo, body)` (PUT), `criar_grupo(body)` (POST),
   `listar_gastos_fixos()` (GET), `criar_gasto_fixo(body)` (POST),
   `atualizar_gasto_fixo(id, body)` (PUT), `excluir_gasto_fixo(id)` (DELETE) — via
   `_autenticado`, conforme `frontend-dashboard.md`.
2. **`api_proxy`:** rotas `PUT /api/grupos/<grupo>`, `POST /api/grupos`,
   `GET/POST /api/gastos-fixos`, `PUT/DELETE /api/gastos-fixos/<int:id>`; padrão
   `try/except httpx.HTTPError → 502`, `_repassar`. Body via
   `request.get_json(silent=True) or {}`. **Não** mexer na rota
   `DELETE /api/grupos/<grupo>` existente.

## Critérios de aceite

- [ ] `PUT/POST /api/grupos*` repassam status e corpo do backend
- [ ] `GET/POST/PUT/DELETE /api/gastos-fixos*` repassam status e corpo do backend
- [ ] Backend fora do ar → `502 {"erro": "backend indisponível"}` em cada rota nova
- [ ] Cada rota chama o método correto do cliente (`assert_called_once_with`)
- [ ] Testes vermelhos antes (TDD); cliente mockado via `BACKEND_CLIENT` + `resposta_factory`

## Verificação local

```bash
uv run pytest tests/frontend/test_proxy_parcelas_assinaturas.py -v
```
