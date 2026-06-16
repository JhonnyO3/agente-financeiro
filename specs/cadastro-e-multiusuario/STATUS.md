# STATUS — cadastro-e-multiusuario

**Gate:** `plan.md` **Aprovado** (2026-06-15). Squad **CONCLUÍDA**. Branch: `feat/squad-parser-cadastro`. Suíte: 699 passed.

| ID | Tarefa | Stack | Depende de | Estado | Worktree/Branch | Nota |
|----|--------|-------|-----------|--------|-----------------|------|
| A (01) | UsuarioRepository.buscar_por_telefone + testes | python | contratos | done | feat/squad-parser-cadastro | onda 1 |
| B (02) | Endpoint GET /auth/identidade/por-telefone | python | A | done | feat/squad-parser-cadastro | onda 2 |
| C (03) | Webhook resolve identidade in-process (remove WHATSAPP_ALLOWED_NUMBER) | python | A | done | feat/squad-parser-cadastro | onda 2 |
| D (04) | Worker: usuario_id + histórico antes de classificar + construir_roteador | python | contratos | done | feat/squad-parser-cadastro | onda 1 |
| E (05) | Wiring main.py + config + estado_store configurável | python | A, C, D | done | feat/squad-parser-cadastro | onda 3 |
| F (06) | Tela de cadastro Flask + BackendClient.criar_usuario | python | contratos | done | feat/squad-parser-cadastro | onda 1 |

## Decisões aplicadas

- #4 endpoint `/auth/identidade` protegido por `get_usuario_atual` (qualquer autenticado).
- #5 pós-cadastro redireciona ao dashboard (sem tela de lista).
- #1 `AGENTE_USUARIO_EMAIL` mantido (não quebra `.env`); `WHATSAPP_ALLOWED_NUMBER` removido.
- #2 repo por mensagem via `repo_factory` + `construir_roteador(repo)` (roteador/tools intocados).
- Resolução de identidade: in-process no webhook (`app.state.session_factory`); endpoint `/auth` existe para uso administrativo.

Todas as tarefas integradas e verdes.
