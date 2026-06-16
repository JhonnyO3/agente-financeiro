# Exploração — cadastro-e-multiusuario

Mapa do território antes de planejar. Somente leitura; nenhum código alterado.

## Estrutura relevante

```
agent/
  config.py                       # Settings (pydantic-settings). Tem WHATSAPP_ALLOWED_NUMBER (remover)
  db.py                           # engine helper do agente (agent.config)
  entrypoint/
    main.py                       # WIRING (lifespan). _SessionFactoryRepository c/ usuario_id FIXO
    webhook.py                    # boundary HTTP. extrair_numero/texto, filtros, dedup, fila
    worker.py                     # fila + micro-debounce + pipeline. BUG: histórico vazio
  services/
    classificador.py              # classificar(mensagem, historico, estado_pendente)
    roteador.py                   # rotear(intencao, usuario_id, agora, contexto). Segura repository
    estado_store.py               # EstadoStoreRedis/Memoria. chave estado:{usuario_id}. _MAX_HISTORICO=5
    formatador.py
  tools/
    cadastrar.py listar.py atualizar.py excluir.py conversar.py   # seguram repository no __init__
backend/
  controllers/auth.py             # router /auth (login/refresh/logout). Padrão a seguir p/ identidade
  controllers/admin.py            # router /admin, dependencies=[Depends(get_admin)]. CRUD usuários
  services/admin_usuarios.py      # criar/listar/atualizar/excluir usuário
  auth/dependencies.py            # get_usuario_atual, get_admin, UsuarioToken, HttpErro
  dtos/usuario.py                 # UsuarioCreateRequest/UpdateRequest/Response
  models/usuario.py               # telefone TEXT nullable + índice único parcial já existe
  repositories/usuario_repository.py  # criar/buscar_por_id/buscar_por_email/listar/...
  dependencies.py                 # get_session, get_session_begin
frontend/
  app.py                          # create_app, before_request protege rotas
  blueprints/auth.py dashboard.py api_proxy.py
  services/backend_client.py      # httpx, _autenticado() com refresh automático
  services/sessao.py              # tokens + role em session
  templates/base.html dashboard/index.html auth/login.html
```

## Convenções reais observadas

- **Camadas Python**: controllers (FastAPI/Flask) → services → repository → models; schemas Pydantic nas DTOs. Segue `rules/python.md`.
- **Async SQLAlchemy 2.0**: repositórios recebem `AsyncSession`. No agente, `_SessionFactoryRepository` envelopa com sessão por chamada (`session_factory.begin()` p/ escrita, `session_factory()` p/ leitura).
- **Isolamento por usuario_id**: `TransacaoRepository` já exige `usuario_id` em toda query; o adapter injeta o id fixo hoje.
- **Backend `/auth`** usa `APIRouter(prefix="/auth")` com handlers que leem `request.app.state.sessionmaker()` e `UsuarioRepository`. Erros via `JSONResponse({"erro": ...}, status_code=...)`.
- **Backend `/admin`** usa `APIRouter(prefix="/admin", dependencies=[Depends(get_admin)])` — proteção por role ADMIN + allowlist `ADMIN_EMAILS`.
- **Frontend Flask**: blueprints registrados em `create_app`; `before_request` redireciona não-autenticado para login; chamadas ao backend via `BackendClient` (httpx) com refresh automático; estado em `session`.
- **Testes**: mocks puros, sem rede/DB/LLM/Redis real. `EstadoStoreMemoria` é o fake do Redis. `test_webhook.py` define env vars no nível do módulo antes de importar o app.

## Pontos de reuso

- `EstadoStoreRedis` já é keyed por `usuario_id` e tem histórico — só falta o worker carregar antes de classificar.
- `_SessionFactoryRepository` já existe; basta parametrizar `usuario_id` por mensagem (virar factory).
- Padrão `/auth` (controllers/auth.py) é o molde exato para o endpoint de resolução por telefone.
- `BackendClient._autenticado` já injeta o Bearer e renova token — a tela de cadastro reusa para chamar `POST /admin/usuarios`.
- `admin_usuarios.criar` + `UsuarioCreateRequest` já fazem o cadastro completo (hash, email único).

## Pontos de integração (costura) — risco de colisão

- `webhook.py` — passa a resolver `usuario_id` e enfileira `(usuario_id, numero, texto)`. Remove `WHATSAPP_ALLOWED_NUMBER`.
- `worker.py` — assinaturas passam a receber `usuario_id`; carrega estado/histórico antes de classificar; usa `repo_factory`.
- `main.py` — wiring: `_SessionFactoryRepository` vira factory; worker recebe `repo_factory`; consumidor desempacota a tupla nova; remove `usuario_id` fixo e `resolver_usuario_id` por email.
- `roteador.py` / `tools/*` — hoje seguram `repository` no `__init__`. Para repo por mensagem, ou (A) `repo` vira parâmetro de `rotear`/`executar`, ou (B) roteador+tools são reconstruídos por mensagem dentro do worker. **Decisão no plan.**

## Descobertas que divergem da spec (atenção)

1. **Tools seguram `repository` no construtor** (não recebem por `executar`). A "Opção A" da spec (repo como parâmetro de `executar`) exige tocar TODAS as tools + roteador + main no mesmo PR — vira um ponto de colisão. Avaliado no plan: usar **repo_factory no worker reconstruindo roteador/tools por mensagem** minimiza a mudança de assinatura pública das tools.
2. `roteador.rotear` hoje recebe `(intencao, usuario_id, agora, contexto)` e usa `self._repo`. O worker atual chama `self._roteador.rotear(intencao)` — **assinatura desatualizada / quebrada**: a integração multi-usuário precisa alinhar isso.
3. `worker._processar` hoje chama `self._classificador.classificar(texto)` mas o classificador exige `(mensagem, historico, estado_pendente)` — **também desalinhado**. Confirma o bug do histórico vazio descrito na spec; na verdade nem compila com a assinatura atual.
4. `registrar_mensagem` do estado_store recebe `(usuario_id, msg, agora)`; o worker chama `(numero, msg)` sem `agora` — desalinhado.
5. `telefone` no `Usuario`/DTO é nullable; manter assim (sem migration). Tela valida obrigatório no front.

## Riscos

- **Vazamento entre usuários** se qualquer query não filtrar por `usuario_id`. Mitigar: repo por mensagem sempre construído com o id resolvido; nenhum caminho usa id fixo.
- **Worker compartilhado**: `_pendentes`/`_locks` hoje são keyed por `numero`. Com multiusuário, dois números distintos já são chaves distintas — ok; mas o lock/pendência deve continuar por `numero` (ou por `usuario_id`) para não misturar fragmentos.
- **`main.py` é ponto único de costura** — várias tasks querem tocá-lo. Concentrar a edição de `main.py` em UMA task (wiring) para evitar conflito.
- Estado in-process exige 1 worker Uvicorn (invariante já documentada) — multiusuário não muda isso.
