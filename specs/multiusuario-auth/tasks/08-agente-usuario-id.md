# Tarefa 08 — Agente grava usuario_id do usuário padrão

**Stack:** python
**Depende de:** 03
**Contrato:** `schema-usuarios.md`

## Objetivo
Resolver o `usuario_id` do usuário-dono do número autorizado no lifespan e gravá-lo nas transações criadas.

## Arquivos (posse exclusiva)
- `agent/entrypoint/main.py`
- `agent/config.py` (adicionar `AGENTE_USUARIO_EMAIL`, default `jhonatas2004@gmail.com`)
- `agent/services/cadastrar.py`
- `tests/test_agente_usuario_id.py`

## Escopo
1. No lifespan, resolver `usuario_id` por `AGENTE_USUARIO_EMAIL` via `backend.repositories.UsuarioRepository.buscar_por_email` (import in-process).
2. Injetar `usuario_id` no `CadastrarService`; preencher `TransacaoCreate.usuario_id`.
3. Sem multi-número; comportamento single-user preservado.

## Critérios de aceite
- [ ] Transação criada pelo agente nasce com o `usuario_id` correto.
- [ ] Consultas do agente seguem funcionando para o usuário padrão.

## Verificação
```bash
uv run pytest tests/test_agente_usuario_id.py -v
```
