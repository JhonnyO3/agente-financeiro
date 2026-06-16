# Tarefa E (05) — Wiring main.py + config + estado_store configurável

**Stack:** python
**Depende de:** A, C, D
**Contratos:** `worker-pipeline.md`, `roteador-tools.md`, `resolucao-identidade.md`

## Objetivo

Ponto de costura final: tornar `_SessionFactoryRepository` uma factory por mensagem, montar `construir_roteador`, expor `session_factory`/`repo_factory` em `app.state`, desempacotar a tupla nova no consumidor, remover o `usuario_id` fixo e `resolver_usuario_id` por email, remover `WHATSAPP_ALLOWED_NUMBER` da config e tornar o histórico configurável.

## Arquivos (posse exclusiva)

- `agent/entrypoint/main.py`
- `agent/config.py`
- `agent/services/estado_store.py`
- `tests/test_estado_store.py`
- `tests/test_main_wiring.py`

## Escopo

### main.py
1. `_criar_repo_factory(session_factory)` → `factory(usuario_id) -> _SessionFactoryRepository`.
2. `_criar_construir_roteador(relogio, embedder, estado_store)` → `construir(repo) -> Roteador` (instancia RAG + 5 tools + Roteador por repo). Ver `roteador-tools.md`.
3. `Worker(... , repo_factory, construir_roteador, ...)` conforme contrato.
4. `app.state.session_factory` e `app.state.repo_factory` expostos; remover `app.state.usuario_id`.
5. Consumidor: `usuario_id, numero, texto = await fila.get()` → `worker.receber(usuario_id, numero, texto)`.
6. Remover `resolver_usuario_id(...)` e a resolução por `AGENTE_USUARIO_EMAIL` do startup.
7. `EstadoStoreRedis` construído com os limites de histórico configuráveis (ver abaixo).

### config.py
8. Remover o campo `WHATSAPP_ALLOWED_NUMBER`.
9. Adicionar `HISTORICO_MAX_MENSAGENS: int = 10` e `HISTORICO_TTL_HORAS: int = 2`.
10. `AGENTE_USUARIO_EMAIL`: manter como deprecado (não usar no fluxo) ou remover — seguir a decisão do plan (recomendado manter para não quebrar `.env`).

### estado_store.py
11. Tornar `_MAX_HISTORICO` configurável (param de `EstadoStoreRedis`/`Memoria`, default 10) e o TTL de inatividade do histórico configurável (`HISTORICO_TTL_HORAS`). `registrar_mensagem` passa a definir/renovar `historico_expira_em = agora + ttl`.

## Critérios de aceite → teste

- [ ] App importa e sobe (lifespan) sem `WHATSAPP_ALLOWED_NUMBER` definido
- [ ] `app.state.session_factory` e `app.state.repo_factory` existem; `repo_factory(7)` devolve repo com usuario_id=7
- [ ] Consumidor desempacota `(usuario_id, numero, texto)` e chama `worker.receber` com os 3
- [ ] `estado_store` respeita `HISTORICO_MAX_MENSAGENS` (mantém só as últimas N)
- [ ] Histórico expira após `HISTORICO_TTL_HORAS` de inatividade
- [ ] Nenhuma referência a `WHATSAPP_ALLOWED_NUMBER` no código

## Verificação local

```bash
uv run pytest tests/test_estado_store.py tests/test_main_wiring.py -v
uv run pytest -q
```
