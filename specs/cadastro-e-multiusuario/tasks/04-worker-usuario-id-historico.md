# Tarefa D (04) — Worker: usuario_id, histórico antes de classificar, construir_roteador

**Stack:** python
**Depende de:** contratos congelados
**Contratos:** `worker-pipeline.md`, `roteador-tools.md`

## Objetivo

Reescrever o pipeline do worker para multi-usuário: receber `usuario_id`, carregar o estado/histórico **antes** de classificar (corrige o bug de histórico vazio e as assinaturas hoje quebradas), e obter o roteador escopado por mensagem via `construir_roteador(repo)`.

## Arquivos (posse exclusiva)

- `agent/entrypoint/worker.py`
- `tests/test_worker.py`

## Escopo

1. `Worker.__init__` passa a receber `construir_roteador: Callable[[repo], Roteador]` e `repo_factory` (ou um único `construir_roteador` que já recebe o repo) em vez de `roteador`/`repository` fixos. Mantém `classificador`, `formatador`, `evolution_client`, `estado_store`, `debounce_segundos`.
2. `receber(usuario_id, numero, texto)` e `processar_pendentes` preservam o `usuario_id` junto dos fragmentos. `_pendentes`/`_locks` continuam keyed por `numero`.
3. `_processar(usuario_id, numero, texto)` na ordem do contrato:
   - `estado = await estado_store.obter(usuario_id, agora)` ANTES de classificar
   - `registrar_mensagem(usuario_id, msg_usuario, agora)`
   - `classificar(mensagem=texto, historico=[f"{m.papel}: {m.texto}" ...], estado_pendente=resumir_pendencia(estado))`
   - `repo = repo_factory(usuario_id)` ; `roteador = construir_roteador(repo)`
   - `rotear(intencao, usuario_id, agora, {"mensagem": texto})`
   - `formatar` ; `registrar_mensagem(usuario_id, msg_assistente, agora)` ; `enviar_mensagem(numero, resposta)`
4. Manter o `try/except` com mensagem amigável ao `numero`.

## Critérios de aceite → teste

- [ ] `_processar` chama `estado_store.obter` ANTES de `classificar`
- [ ] Classificador recebe `historico` não-vazio quando há histórico prévio
- [ ] `registrar_mensagem` é chamado com `(usuario_id, msg, agora)`
- [ ] Dois usuários (ids distintos) processados isoladamente: cada um usa o repo do seu id (`construir_roteador` recebe repos distintos)
- [ ] Erro no pipeline → envia mensagem amigável ao número e não derruba o worker

> Usar `EstadoStoreMemoria` como fake, classificador/roteador/formatador mockados, `construir_roteador` como spy que registra o repo recebido.

## Verificação local

```bash
uv run pytest tests/test_worker.py -v
```
