# Contrato: Worker + Pipeline multi-usuário

**Status:** Congelado
**Fronteira:** `webhook.py` → `fila` → `worker.py` → (`estado_store`, `classificador`, `roteador`, `formatador`, `evolution`)

Define como `usuario_id` flui da fila ao pipeline, como o histórico é carregado **antes** de classificar, e como o repositório é resolvido por mensagem via `repo_factory`.

## 1. Formato da fila (app.state.fila)

```python
# Item da fila — TUPLA de 3
(usuario_id: int, numero: str, texto: str)
```

- Webhook enfileira `(usuario.id, numero, texto)` após resolver identidade.
- Consumidor no `lifespan` desempacota os 3 e chama `worker.receber(usuario_id, numero, texto)`.

## 2. app.state exposto pelo lifespan

```python
app.state.fila              # asyncio.Queue de tuplas (usuario_id, numero, texto)
app.state.worker            # Worker
app.state.estado_store      # EstadoStoreRedis
app.state.evolution_client  # EvolutionApiClient
app.state.session_factory   # async_sessionmaker  ← NOVO: usado pela resolução in-process
app.state.repo_factory      # Callable[[int], repo]  ← NOVO
```

- **Removidos:** `app.state.usuario_id` (id fixo) e `resolver_usuario_id(...)` por email.
- `WHATSAPP_ALLOWED_NUMBER` e `AGENTE_USUARIO_EMAIL` **deixam de gatilhar** o caminho do agente (ver `config` no plan).

## 3. repo_factory

```python
def _criar_repo_factory(session_factory) -> Callable[[int], _SessionFactoryRepository]:
    def factory(usuario_id: int) -> _SessionFactoryRepository:
        return _SessionFactoryRepository(session_factory, usuario_id)
    return factory
```

- `_SessionFactoryRepository(session_factory, usuario_id)` permanece **inalterado** na sua API pública (mesmos métodos). Só deixa de ser instanciado uma vez com id fixo.
- **Invariante de isolamento:** o repo é sempre construído com o `usuario_id` resolvido na mensagem. Nenhum caminho usa id fixo de processo.

## 4. Worker — assinaturas (Congelado)

```python
class Worker:
    def __init__(
        self,
        classificador, formatador, evolution_client, estado_store,
        construir_roteador: Callable[[repo], Roteador],   # ver roteador-tools.md
        debounce_segundos=5,
    ) -> None: ...

    async def receber(self, usuario_id: int, numero: str, texto: str) -> None: ...

    async def processar_pendentes(self) -> None: ...

    async def _processar(self, usuario_id: int, numero: str, texto: str) -> None: ...
```

- `_pendentes` e `_locks` continuam keyed por **`numero`** (serialização por número de origem). O `usuario_id` é guardado junto do fragmento para uso no processamento.
- Sugestão: `self._pendentes[numero] = (usuario_id, [fragmentos...])` ou estrutura equivalente que preserve o `usuario_id`.

## 5. _processar — ordem obrigatória (corrige o bug do histórico vazio)

```python
async def _processar(self, usuario_id, numero, texto):
    agora = datetime.now(timezone.utc)

    # 1. CARREGA estado ANTES de classificar
    estado = await self._estado_store.obter(usuario_id, agora)

    # 2. Registra a mensagem do usuário no histórico
    await self._estado_store.registrar_mensagem(
        usuario_id, Mensagem(papel="usuario", texto=texto, em=agora), agora
    )

    # 3. Classifica COM histórico + pendência resumida
    from agent.services.estado_store import resumir_pendencia
    intencao = await self._classificador.classificar(
        mensagem=texto,
        historico=[f"{m.papel}: {m.texto}" for m in estado.historico],
        estado_pendente=resumir_pendencia(estado),
    )

    # 4. Repo por mensagem + roteador escopado
    repo = self._repo_factory(usuario_id)          # via construir_roteador
    roteador = self._construir_roteador(repo)
    resultado = await roteador.rotear(intencao, usuario_id, agora, {"mensagem": texto})

    # 5. Formata e registra resposta + envia
    resposta = self._formatador.formatar(resultado)
    await self._estado_store.registrar_mensagem(
        usuario_id, Mensagem(papel="assistente", texto=resposta, em=agora), agora
    )
    await self._evolution.enviar_mensagem(numero, resposta)
```

- **Crítico:** `obter` (passo 1) acontece **antes** de `registrar_mensagem` (passo 2) para que o histórico passado ao classificador seja o anterior à mensagem atual (não inclua a própria).
- `registrar_mensagem` exige `(usuario_id, msg, agora)` — alinhar com `estado_store.py` (corrige a chamada atual sem `agora`).
- Tratamento de erro: mantém o `try/except` atual que envia mensagem amigável ao `numero`.

## 6. Histórico — configuração

- `_MAX_HISTORICO`: 5 → **10**, configurável via env `HISTORICO_MAX_MENSAGENS` (default 10).
- `historico_expira_em`: TTL de inatividade configurável via env `HISTORICO_TTL_HORAS` (default 2h).
- Chave Redis permanece `estado:{usuario_id}` (RN-14). Isolamento de histórico garantido pela chave.

## Invariantes de isolamento (inviolável)

- Toda leitura/escrita de transação passa por `repo = repo_factory(usuario_id)` da mensagem.
- Estado e histórico keyed por `usuario_id` no Redis.
- Dois usuários simultâneos → dois `usuario_id` → dois repos → duas chaves Redis. Sem estado compartilhado mutável entre eles no pipeline.
