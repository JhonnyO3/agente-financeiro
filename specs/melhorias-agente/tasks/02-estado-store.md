# Tarefa 02 — Estado: EstadoConversa + EstadoStore (Redis + memória)

**Stack:** python
**Depende de:** 00
**Contrato:** `estado-store.md`

## Objetivo
Modelos de estado conversacional + interface async `EstadoStore` + `EstadoStoreRedis` (produção) + `EstadoStoreMemoria` (testes/dev).

## Arquivos (posse exclusiva)
- `agent/domain/estado.py`
- `agent/services/estado_store.py`
- `tests/test_estado_store.py`
- `pyproject.toml` (adicionar dependência `redis>=5` — única mudança permitida no arquivo)
- `docker-compose.yml` (adicionar serviço `redis` — única mudança permitida no arquivo)

## Escopo
1. `estado.py`: `Mensagem`, `OpcaoPendente`, `EstadoConversa` conforme contrato.
2. `estado_store.py`: `Protocol EstadoStore` **async** + `EstadoStoreMemoria` + `EstadoStoreRedis` (`redis.asyncio`, chave `estado:{usuario_id}`, JSON via `model_dump_json`/`model_validate_json`, TTL físico 24h renovado em escrita), todos com `agora` injetado.
3. TTL lógico: pendência 5 min × histórico 24h (independentes, decididos em `obter`). `registrar_mensagem` corta em N=5.
4. `resumir_pendencia(estado) -> str` cobrindo os formatos de `{estado_pendente}` de `classificador.md`.
5. `uv add redis` (`redis>=5`); serviço `redis:7-alpine` no `docker-compose.yml`.

## Critérios de aceite
- [ ] `EstadoStoreRedis` (cliente `AsyncMock`) e `EstadoStoreMemoria` passam a MESMA suíte de comportamento — sem Redis real.
- [ ] `obter` em chave inexistente devolve estado limpo (não None).
- [ ] Pendência expira sem afetar histórico e vice-versa.
- [ ] `limpar_pendencia` preserva histórico; `registrar_mensagem` mantém ≤ 5.

## Verificação
```bash
uv run pytest tests/test_estado_store.py -v
```
