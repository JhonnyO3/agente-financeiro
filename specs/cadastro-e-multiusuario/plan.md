# Plano técnico — cadastro-e-multiusuario

**Status:** Aprovado
**Feature:** `cadastro-e-multiusuario`
**Fonte:** `spec.md` (atualizada com a decisão `/auth`), `exploracao.md`, `contracts/*`

> Gate humano: aprovado por jhonatas em 2026-06-15. Decisões ratificadas: #4 endpoint `/auth/identidade`
> protegido por `get_usuario_atual` (qualquer autenticado); #5 pós-cadastro redireciona ao dashboard
> (sem tela de lista); #1 manter `AGENTE_USUARIO_EMAIL` deprecado; #2 repo via `construir_roteador(repo)`.

---

## Objetivo

1. Tela Flask para admin cadastrar usuário (nome, e-mail, telefone, senha) reusando `POST /admin/usuarios`.
2. Agente multi-usuário: webhook resolve identidade pelo telefone (in-process), isolamento total por `usuario_id`, histórico no Redis carregado antes de classificar, remoção de `WHATSAPP_ALLOWED_NUMBER`.

---

## Decisão arquitetural 1 — Resolução de identidade: in-process vs HTTP `/auth`

**Recomendação adotada: webhook resolve in-process; endpoint `/auth` existe mas o webhook não o usa.**

| Critério | In-process (repo direto) | HTTP `GET /auth/...` |
|---|---|---|
| Latência | Zero hop (mesma sessão de banco) | +1 round-trip HTTP do serviço para ele mesmo |
| Acoplamento | Usa `session_factory` já em `app.state` | Precisa de token de serviço, base_url própria, cliente httpx |
| Testabilidade | Mock do repo (já é o padrão dos testes) | Mock de transporte HTTP, fixtures de resposta |
| Pontos de falha | Nenhum extra | Timeout, auth, indisponibilidade do próprio processo |
| Isolamento de *rules* | Resolução é regra de identidade, fica no agente | Endpoint isola identidade de admin (objetivo do usuário) |

**Por isso:**
- O **webhook usa o caminho in-process** (`resolver_usuario_por_telefone` → `UsuarioRepository.buscar_por_telefone`). É o caminho quente, roda a cada mensagem (RN-16), e não faz sentido o processo chamar a si mesmo por HTTP.
- O **endpoint `GET /auth/identidade/por-telefone/{telefone}` é criado mesmo assim**, sob `/auth` (não `/admin`), atendendo à decisão do usuário de **isolar as regras de identidade das de gestão administrativa**. Serve para diagnóstico/uso administrativo e para deixar o ponto de extensão pronto, sem onerar o webhook.
- Proteção do endpoint: `get_usuario_atual` (Bearer válido) — **não** a allowlist de admin, porque identidade ≠ administração. Detalhes em `contracts/resolucao-identidade.md`.

## Decisão arquitetural 2 — Repo por mensagem: `construir_roteador(repo)` vs `repo` em `executar`

**Recomendação adotada: factory `construir_roteador(repo)` que reconstrói roteador+tools por mensagem.**

A spec sugeria "repo como parâmetro de `executar`" (Opção A). Na prática as tools **seguram `repository` no construtor** e o roteador também. Threadar `repo` por todas as assinaturas `executar` tocaria 5 tools + roteador + main no mesmo PR (colisão alta, quebra testes existentes das tools). A factory:

- Mantém **inalteradas** as assinaturas de `roteador.py` e `tools/*` (zero edição nesses arquivos → mais paralelismo, testes atuais seguem válidos).
- Concentra o wiring em `main.py` e o uso no `worker.py`.
- Custo desprezível (tools são leves). Ver `contracts/roteador-tools.md`.

## Decisão arquitetural 3 — `telefone` continua opcional na API; sem migration

Mantém `telefone: str | None` no modelo/DTO e índice único parcial existente. A obrigatoriedade vale só no front (tela). Usuários sem telefone simplesmente nunca resolvem no webhook. Evita migration e breaking change.

---

## Arquitetura-alvo (fluxo)

```
WhatsApp → Evolution → POST /webhook/mensagem
  apikey + filtros + dedup (inalterado)
  numero = extrair_numero ; texto = extrair_texto
  usuario = resolver_usuario_por_telefone(app.state, numero)   ← in-process, repo
     None → 200 silencioso (não cadastrado OU inativo)
     ativo → fila.put((usuario.id, numero, texto))
        │
   consumidor lifespan → worker.receber(usuario_id, numero, texto)
        │  (micro-debounce)
   worker._processar(usuario_id, numero, texto):
     estado = estado_store.obter(usuario_id, agora)          # ANTES de classificar
     estado_store.registrar_mensagem(usuario_id, msg_user, agora)
     intencao = classificador.classificar(texto, historico=estado.historico, estado_pendente=...)
     repo = repo_factory(usuario_id)
     roteador = construir_roteador(repo)
     resultado = roteador.rotear(intencao, usuario_id, agora, {"mensagem": texto})
     resposta = formatador.formatar(resultado)
     estado_store.registrar_mensagem(usuario_id, msg_assistente, agora)
     evolution.enviar_mensagem(numero, resposta)
```

---

## Tarefas (DAG)

| ID | Tarefa | Stack | Depende de | Arquivos de posse exclusiva |
|----|--------|-------|-----------|------------------------------|
| A | `buscar_por_telefone` no `UsuarioRepository` + testes | python | contratos | `backend/repositories/usuario_repository.py`, `tests/test_usuario_repository.py` |
| B | Endpoint `GET /auth/identidade/por-telefone/{telefone}` + testes | python | A | `backend/controllers/auth.py`, `tests/test_auth_identidade.py` |
| C | Webhook resolve identidade in-process + remove `WHATSAPP_ALLOWED_NUMBER` | python | A | `agent/entrypoint/webhook.py`, `tests/test_webhook.py` |
| D | Worker recebe `usuario_id`, carrega histórico antes de classificar, usa `construir_roteador` | python | contratos | `agent/entrypoint/worker.py`, `tests/test_worker.py` |
| E | Wiring `main.py`: `repo_factory`, `construir_roteador`, consumidor da tupla, remove id fixo; config (`HISTORICO_MAX_MENSAGENS`, `HISTORICO_TTL_HORAS`, remoção de `WHATSAPP_ALLOWED_NUMBER`); `estado_store` configurável | python | A, C, D | `agent/entrypoint/main.py`, `agent/config.py`, `agent/services/estado_store.py`, `tests/test_estado_store.py`, `tests/test_main_wiring.py` |
| F | Tela de cadastro Flask + método no `BackendClient` | python | contratos | `frontend/blueprints/admin_usuarios.py`, `frontend/templates/admin/usuarios_novo.html`, `frontend/services/backend_client.py`, `frontend/app.py`, `tests/test_frontend_cadastro.py` |

### DAG resumido

```
contratos ─┬─ A ─┬─ B
           │     ├─ C ──┐
           │     └──────┤
           ├─ D ────────┤
           │            └─ E   (integra webhook + worker + wiring)
           └─ F                (paralelo total — só depende de contratos)
```

- **A** primeiro (base do repo). **B**, **C** dependem de A.
- **D** só depende de contratos (worker contra contrato de `construir_roteador`/`estado_store`); pode correr em paralelo com A/B/C/F.
- **E** é o ponto de costura final: precisa de A (repo factory), C (formato da fila/webhook) e D (Worker novo). **E é a única task que toca `main.py`** — evita colisão.
- **F** é totalmente independente (frontend), paralela a tudo.

### Anti-colisão (verificação)

- `main.py` → só **E**. `webhook.py` → só **C**. `worker.py` → só **D**. `config.py`/`estado_store.py` → só **E**.
- `roteador.py` e `tools/*` → **ninguém edita** (decisão 2). Sem colisão.
- `usuario_repository.py` → só **A**. `auth.py` (backend) → só **B**. `backend_client.py` → só **F** (único consumidor desta feature).
- Cada task possui seu próprio arquivo de teste (sem dois agentes no mesmo `test_*.py`).

> Atenção: **C** e **D** ambos preparam o terreno para **E**, mas não compartilham arquivos entre si (webhook.py vs worker.py). **E** depende de ambos por **semântica** (precisa do webhook e do worker novos prontos), não por arquivo.

---

## Ordem de integração

1. **A** (repo) — base.
2. **B**, **C**, **D**, **F** em paralelo (B e C atrás de A; D e F livres).
3. **E** por último (wiring): junta webhook+worker+config, roda a suíte completa.
4. Verificação total: `uv run pytest -q`.

---

## Verificação

| Requisito | Como testar |
|---|---|
| `buscar_por_telefone` (ativo/inativo/inexistente/normalização) | `pytest tests/test_usuario_repository.py` |
| Endpoint `/auth/identidade/...` (200/204/401) | `pytest tests/test_auth_identidade.py` |
| Número desconhecido/inativo descartado | `pytest tests/test_webhook.py` |
| Histórico carregado antes de classificar + isolamento A×B | `pytest tests/test_worker.py` |
| Histórico configurável + persistência | `pytest tests/test_estado_store.py` |
| Wiring sobe sem `WHATSAPP_ALLOWED_NUMBER` | `pytest tests/test_main_wiring.py` |
| Tela de cadastro (sucesso/duplicado/validação/não-admin) | `pytest tests/test_frontend_cadastro.py` |
| Suíte completa | `uv run pytest -q` |

---

## Riscos e pontos para o humano revisar

1. **`config.py` remove `WHATSAPP_ALLOWED_NUMBER`** — qualquer `.env`/deploy que ainda o defina segue ok (pydantic `extra="ignore"`), mas remover o campo é breaking se algo o lê. Confirmado: só `webhook.py` lê (sai na task C). `AGENTE_USUARIO_EMAIL` deixa de ser usado para resolver o dono — manter o campo no Settings (não quebra) ou remover? **Recomendo manter** para não exigir mudança de `.env` imediata; marcar como deprecado.
2. **Worker `_pendentes`/`_locks` por `numero`** — preciso preservar o `usuario_id` junto do fragmento. Se um mesmo número pudesse mapear a dois usuários (não pode, índice único), não haveria ambiguidade. Documentado no contrato.
3. **Proteção do endpoint `/auth/identidade`** — decisão: `get_usuario_atual` (qualquer autenticado), não admin. Se o humano quiser proteção mais forte (token de serviço dedicado), ajustar antes de aprovar. Como o webhook NÃO usa o endpoint, a escolha é de baixo impacto.
4. **Assinaturas hoje quebradas** (`worker` chama `classificar(texto)` e `rotear(intencao)` com assinaturas antigas) — a task D as corrige conforme o contrato; é mais que "adicionar histórico", é realinhar o pipeline. Esforço de D é o maior.
5. **`construir_roteador` instancia tools por mensagem** — validar que nenhuma tool tem estado caro de construção (RAG cria `BuscaRAG` leve). Confirmado leve.
6. **Tela: lista de usuários** — a spec redireciona para "lista de usuários" após 201. Não existe tela de lista no front hoje; F redireciona para o dashboard ou cria lista mínima. Decisão de escopo para o humano: criar a lista ou só redirecionar?
