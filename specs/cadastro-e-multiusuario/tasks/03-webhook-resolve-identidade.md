# Tarefa C (03) — Webhook resolve identidade in-process

**Stack:** python
**Depende de:** A
**Contratos:** `resolucao-identidade.md` (seção A), `worker-pipeline.md` (formato da fila)

## Objetivo

Substituir o filtro `WHATSAPP_ALLOWED_NUMBER` por resolução de identidade in-process: busca o usuário pelo telefone via `UsuarioRepository` e enfileira `(usuario.id, numero, texto)`. Número não cadastrado ou inativo → discard silencioso (200).

## Arquivos (posse exclusiva)

- `agent/entrypoint/webhook.py`
- `tests/test_webhook.py`

## Escopo

1. Remover `_allowed_number()` e o filtro `if numero != _allowed_number()`.
2. Após extrair `numero`/`texto` (e dedup), resolver identidade:
   ```python
   async def resolver_usuario_por_telefone(app_state, numero):
       async with app_state.session_factory() as session:
           return await UsuarioRepository(session).buscar_por_telefone(numero)
   ```
   (helper local ao webhook, usando `request.app.state.session_factory`).
3. `usuario is None` → `JSONResponse(200, {"status": "ok"})` (discard).
4. Caso contrário → `await request.app.state.fila.put((usuario.id, numero, texto))`.
5. Manter intactos: auth apikey, filtro de evento/`fromMe`, `extrair_texto`, dedup.

## Critérios de aceite → teste

- [ ] Número não cadastrado → não enfileira, retorna 200
- [ ] Usuário inativo (repo retorna None) → não enfileira, retorna 200
- [ ] Usuário ativo → enfileira tupla `(usuario_id, numero, texto)`
- [ ] apikey inválida ainda retorna 401
- [ ] `fromMe`, evento errado, texto vazio, duplicado → 200 sem enfileirar (inalterado)
- [ ] Nenhuma referência a `WHATSAPP_ALLOWED_NUMBER` no arquivo

> Mockar `app.state.session_factory` e `app.state.fila` (fila fake). Repo retorna usuário fake/None.

## Verificação local

```bash
uv run pytest tests/test_webhook.py -v
```
