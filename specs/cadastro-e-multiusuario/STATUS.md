# STATUS — cadastro-e-multiusuario

**Gate:** aguardando aprovação humana do `plan.md` (Status: Rascunho). Squad NÃO iniciada.

| ID | Tarefa | Stack | Depende de | Estado | Worktree/Branch | Nota |
|----|--------|-------|-----------|--------|-----------------|------|
| A (01) | UsuarioRepository.buscar_por_telefone + testes | python | contratos | todo | — | — |
| B (02) | Endpoint GET /auth/identidade/por-telefone | python | A | todo | — | — |
| C (03) | Webhook resolve identidade in-process (remove WHATSAPP_ALLOWED_NUMBER) | python | A | todo | — | — |
| D (04) | Worker: usuario_id + histórico antes de classificar + construir_roteador | python | contratos | todo | — | — |
| E (05) | Wiring main.py + config + estado_store configurável | python | A, C, D | todo | — | — |
| F (06) | Tela de cadastro Flask + BackendClient.criar_usuario | python | contratos | todo | — | — |

## DAG

```
contratos ─┬─ A ─┬─ B
           │     └─ C ─┐
           ├─ D ───────┤
           │           └─ E
           └─ F
```

- **A** base do repo. **B** e **C** atrás de A. **D** e **F** só dependem de contratos.
- **E** é a costura final (única task que toca `main.py`), depende de A+C+D.
- **F** (frontend) paralela a tudo.

## Anti-colisão

- `main.py` → só E · `webhook.py` → só C · `worker.py` → só D · `config.py`/`estado_store.py` → só E.
- `roteador.py`/`tools/*` → ninguém edita (factory de roteador no wiring).
- `usuario_repository.py` → A · `backend/controllers/auth.py` → B · `frontend/*` → F.
- Cada task tem arquivo de teste próprio.

## Contratos congelados

- `usuario-repository.md` · `resolucao-identidade.md` · `worker-pipeline.md` · `roteador-tools.md` · `tela-cadastro.md`
