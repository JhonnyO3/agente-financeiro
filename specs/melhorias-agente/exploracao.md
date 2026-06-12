# Exploração — melhorias-agente

**Data:** 2026-06-12
**Escopo:** `agent/` completo + pontos de toque com `backend/` e `prompts/`

---

## 1. Estrutura atual de `agent/`

### 1.1 Mapa de módulos

```
agent/
├── config.py                      # Settings (pydantic-settings)
├── db.py                          # engine/sessão — CÓDIGO MORTO (confirmado)
├── entrypoint/
│   ├── main.py                    # FastAPI + lifespan: DI completa + _processar_e_responder
│   ├── webhook.py                 # POST /webhook/mensagem
│   └── debounce.py                # MessageDebouncer (buffer + timer 10s por número)
├── integrations/
│   └── evolution_client.py        # EvolutionApiClient (httpx)
├── agents/                        # "chains" LangChain — cada uma é um structured output
│   ├── base.py                    # criar_llm(), criar_llm_formatacao(), carregar_prompt(), coagir_data()
│   ├── classificador.py           # IntencaoResult (8 rótulos) — prompt em prompts/intencao.md
│   ├── extrator.py                # ExtracaoResult — prompt em prompts/sistema.md
│   ├── categorizador.py           # CategoriacaoResult — prompt em prompts/categorizacao.md
│   ├── extrator_alteracao.py      # ExtracaoAlteracaoResult — prompt INLINE
│   ├── extrator_parcelas.py       # ExtratorParcelasResult — prompt INLINE
│   ├── extrator_exclusao_lote.py  # filtros de exclusão — prompt INLINE
│   ├── extrator_lista.py          # ExtracaoListaResult (itens[]) — prompt INLINE extenso
│   ├── filtro_consulta.py         # FiltroConsultaResult — prompt INLINE
│   ├── confirmacao_chain.py       # ConfirmacaoResposta Literal["sim","nao","parcela","grupo"] — INLINE
│   └── embedder.py                # OpenAIEmbeddings text-embedding-3-small
└── services/
    ├── pipeline.py                # Roteador central: estado → tool; sem estado → classificador → tool
    ├── confirmacao_state.py       # ConfirmacaoState (dict in-memory, TTL 5min, UTC-aware)
    ├── cadastrar.py               # CadastrarService (Decimal puro, datas, parcelas)
    ├── alterar.py                 # AlterarService (RAG + confirmação)
    ├── excluir.py                 # ExcluirService (individual, grupo, lote)
    ├── marcar_pago.py             # MarcarPagoService (status → PAGO via RAG)
    ├── consultar.py               # ConsultarService (mensal/semanal/grupo_parcela/geral)
    ├── formatador.py              # Formatador (gpt-4o para tudo menos lote e aguarda_confirmacao)
    └── parcelas.py                # Funções puras sem IO: adicionar_meses, status_por_data, etc.
```

### 1.2 Responsabilidades por camada

| Camada | Responsabilidade real |
|---|---|
| `entrypoint/webhook.py` | Filtra: evento, fromMe, número autorizado (`WHATSAPP_ALLOWED_NUMBER`), texto presente. Sem autenticação por header. |
| `entrypoint/debounce.py` | Buffer por número; reinicia timer de 10s a cada mensagem; junta com `" ".join` (bug: deveria ser `"\n"`); `asyncio.ensure_future` sem guardar referência (risco de GC). |
| `entrypoint/main.py` | Monta toda a DI no lifespan; cria `_SessionFactoryRepository`; resolve `usuario_id` por email no boot; expõe `app.state.*`. |
| `agents/*` | Classes thin com `criar_llm().with_structured_output(Schema)`. Sem lógica de negócio. |
| `services/pipeline.py` | Dois ramos: (a) estado pendente ≠ None → `_rotear_estado` (nunca chama classificador); (b) sem estado → classificador → `_rotear_intencao`. |
| `services/cadastrar.py` | Toda a matemática de parcelas em Decimal. Re-extrai com LLM ao confirmar parcelas/recorrência (bug custoso). |
| `services/alterar.py` | Embeda a mensagem crua (bug: verbos de comando poluem o vetor). |
| `services/formatador.py` | gpt-4o para `cadastro`, `consulta`, `confirmacao`, `fora_escopo`. Lote e `aguarda_confirmacao` são Python puro. |
| `services/parcelas.py` | Funções puras testadas. Reutilizável na refatoração. |

---

## 2. API do data layer reusável (`backend/`)

### 2.1 `backend/repositories/transacao_repository.py`

Todas as assinaturas são `async`. `usuario_id` é filtro opcional em todas as queries — quando `None`, não filtra (usado pelo backend REST); quando fornecido (via `_SessionFactoryRepository`), garante isolamento multiusuário.

| Método | Parâmetros | Retorno |
|---|---|---|
| `criar` | `transacao: TransacaoCreate` | `Transacao` |
| `criar_lote` | `transacoes: list[TransacaoCreate]` | `list[Transacao]` |
| `buscar_por_id` | `id: int, usuario_id: int \| None` | `Transacao \| None` |
| `buscar_por_grupo` | `grupo_parcela_id: UUID, usuario_id: int \| None` | `list[Transacao]` (ordenada por `parcela_numero`) |
| `buscar_semantico` | `embedding: list[float], limite: int = 5, usuario_id: int \| None` | `list[Transacao]` |
| `buscar_semantico_com_distancia` | `embedding: list[float], limite: int = 1, usuario_id: int \| None` | `tuple[Transacao, float] \| None` |
| `atualizar` | `id: int, dados: TransacaoUpdate, usuario_id: int \| None` | `Transacao` |
| `excluir` | `id: int, usuario_id: int \| None` | `None` |
| `excluir_grupo` | `grupo_parcela_id: UUID, usuario_id: int \| None` | `int` (rowcount) |
| `excluir_por_filtros` | `inicio: date, fim: date, categoria: str \| None, usuario_id: int \| None` | `int` (rowcount) |
| `contar_por_filtros` | `inicio: date, fim: date, categoria: str \| None, usuario_id: int \| None` | `int` |
| `listar_por_periodo` | `inicio: date, fim: date, usuario_id: int \| None` | `list[Transacao]` (ordem por data) |
| `listar_por_periodo_com_embedding` | `inicio: date, fim: date, usuario_id: int \| None` | `list[Transacao]` (com embedding não-deferred) |
| `agregar_por_categoria` | `inicio: date, fim: date, usuario_id: int \| None` | `list[AgregadoCategoria]` |

**Observação crítica:** `buscar_semantico_com_distancia` aceita `limite: int = 1` mas sempre retorna apenas a primeira linha (`.first()`), independente do limite passado. Para as 3 faixas de decisão da spec (match confiante / zona ambígua / abaixo do piso), o método precisaria retornar `list[tuple[Transacao, float]]` ou será necessário adicionar um método novo sem quebrar o contrato atual.

### 2.2 `backend/repositories/usuario_repository.py`

| Método | Parâmetros | Retorno |
|---|---|---|
| `criar` | `usuario: UsuarioCreate \| None, **kwargs` | `Usuario` |
| `buscar_por_id` | `id: int` | `Usuario \| None` |
| `buscar_por_email` | `email: str` | `Usuario \| None` (normaliza lowercase) |
| `listar` | — | `list[Usuario]` |
| `atualizar` | `id: int, dados: UsuarioUpdate \| None, **kwargs` | `Usuario` |
| `excluir` | `id: int` | `None` |

### 2.3 `backend/repositories/dtos.py` — dataclasses

**`TransacaoCreate`** (campos obrigatórios sem default):
`usuario_id: int`, `tipo: TipoEnum`, `valor: Decimal`, `descricao: str | None`, `categoria: CategoriaEnum`, `data: date`, `parcela_numero: int`, `parcela_total: int`, `grupo_parcela_id: UUID`, `embedding: list[float]`

Defaults: `status=PENDENTE`, `forma_pagamento=PIX`, `recorrente=False`, `responsavel="Jhonatas"`, `detalhes=None`

**`TransacaoUpdate`** (todos opcionais, default `None`):
`tipo`, `valor`, `descricao`, `categoria`, `data`, `status`, `forma_pagamento`, `recorrente`, `responsavel`, `detalhes`

**`AgregadoCategoria`**: `categoria: CategoriaEnum`, `total: Decimal`, `quantidade: int`

**`UsuarioCreate`**: `nome`, `username`, `email`, `senha_hash`, opcionais: `telefone`, `role=USER`, `ativo=True`

**Problema identificado:** `responsavel="Jhonatas"` hardcoded como default em `TransacaoCreate` (`dtos.py:31`). A refatoração precisa lidar com isso sem alterar `backend/` — o valor deve ser preenchido explicitamente pela Tool Cadastrar antes de criar o DTO.

### 2.4 `backend/models/enums.py`

```python
TipoEnum:            GASTO | INVESTIMENTO | RECEITA
CategoriaEnum:       ALIMENTACAO | TRANSPORTE | LAZER | EDUCACAO | GASTOS_FIXOS
                     | COMPRAS | GASTOS_PONTUAIS | INVESTIMENTO | RECEITA
StatusEnum:          PAGO | PENDENTE
FormaPagamentoEnum:  CARTAO_CREDITO | CARTAO_DEBITO | PIX | BOLETO
RoleEnum:            ADMIN | USER
```

**Ausente:** `DINHEIRO` em `FormaPagamentoEnum` — a spec (`prompt-base.md`) menciona como forma válida, mas o enum não tem. Precisará de migração Alembic se for adicionado.

### 2.5 `backend/models/transacao.py` — ORM

Tabela `transacoes`. Colunas presentes e relevantes para a refatoração:
- `recorrente: bool` — existe (server_default `false`)
- `detalhes: str | None` — existe
- `responsavel: str` — existe (server_default `"Jhonatas"`)
- `forma_pagamento: FormaPagamentoEnum` — existe
- `grupo_parcela_id: str` — stored como VARCHAR/UUID-string (não UUID nativo)
- `embedding: vector(1536)` — deferred (não carregado por default nas queries)

**Sem `updated_at`/`atualizado_em`:** a tabela tem apenas `criado_em`.

---

## 3. Wiring atual (`main.py`)

### 3.1 Fluxo do lifespan

```python
# agent/entrypoint/main.py:124-213
lifespan:
  1. create_async_engine(settings.DATABASE_URL)
  2. async_sessionmaker(engine, expire_on_commit=False)
  3. resolver_usuario_id(UsuarioRepository, email)           # busca id no boot
  4. EvolutionApiClient(base_url, instance, api_key)
  5. Embedder()
  6. ConfirmacaoState()                                      # in-memory
  7. _SessionFactoryRepository(session_factory, usuario_id)  # adapter
  8. Instancia todos os services e chains                    # 10 objetos
  9. Pipeline(...)
  10. _processar_e_responder(numero, texto)                  # closure pipeline + evolution_client
  11. MessageDebouncer()                                     # in-memory
  → app.state.{pipeline, evolution_client, debouncer, processar_e_responder}
```

### 3.2 `_SessionFactoryRepository` (adapter)

`main.py:31-112`. Envolve `TransacaoRepository` com gestão de sessão por chamada:
- Writes: `session_factory.begin()` (auto-commit via context manager)
- Reads: `session_factory()` (sem begin)

Injeta `usuario_id` fixo em todos os métodos — isolamento multiusuário por instância do adapter.

### 3.3 `resolver_usuario_id` (`main.py:114-121`)

Busca o usuário por `settings.AGENTE_USUARIO_EMAIL` no boot. `RuntimeError` se não encontrado (fail-fast, intencional).

### 3.4 `agent/config.py`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str
    OPENAI_API_KEY: str
    EVOLUTION_API_URL: str
    EVOLUTION_INSTANCE: str
    EVOLUTION_API_KEY: str
    WHATSAPP_ALLOWED_NUMBER: str
    AGENTE_USUARIO_EMAIL: str = "jhonatas2004@gmail.com"  # default hardcoded (problema)
```

**Campos ausentes para a refatoração:** `RESPONSAVEL_PADRAO`, modelos LLM configuráveis, limiares RAG, `WEBHOOK_SECRET` (autenticação).

### 3.5 `agent/db.py` — código morto confirmado

Não é importado por nenhum módulo do agent — o lifespan cria seu próprio engine. Pode ser removido. (Importa `settings` na carga — razão do `os.environ.setdefault` nos testes.)

---

## 4. Convenções de teste

### 4.1 Organização

```
tests/
├── test_webhook.py                  # endpoint FastAPI via ASGITransport; app.state mockado
├── test_pipeline.py                 # Pipeline com deps AsyncMock/MagicMock
├── test_service_cadastrar.py        # CadastrarService com mocks
├── test_service_alterar_excluir.py  # AlterarService/ExcluirService com mocks
├── test_parcelas_helper.py          # funções puras — sem mocks, sem IO
├── tests/backend/                   # backend REST (conftest.py com fixtures de DB)
└── tests/frontend/                  # frontend Flask
```

### 4.2 Padrões observados

- **Env vars antes dos imports**: `test_webhook.py:4-9` usa `os.environ.setdefault` no topo antes de importar o app (Settings roda na carga do módulo).
- **Mocks**: `AsyncMock` para métodos async, `MagicMock` para objetos. Sem DB real, sem LLM real.
- **Imports dentro de funções** em alguns arquivos para evitar settings validation na coleta.
- **asyncio_mode = "auto"** no `pyproject.toml`.
- **Comando**: `uv run pytest tests/ -v`
- Services nos testes: cada test function monta os próprios mocks via helper `_make_service(...)` — sem fixtures pytest.

---

## 5. Infra

### 5.1 Dockerfile / execução

Imagem única compartilhada pelos 3 serviços; Start Command varia:
- **Agente**: `uvicorn agent.entrypoint.main:app --host 0.0.0.0 --port 8001` — **single-process (1 worker)**
- **Backend**: `uvicorn backend.main:app --port 8000`
- **Frontend**: `gunicorn frontend.app:app -w 2 --threads 4`

**Implicação:** o estado in-memory do agente é seguro HOJE (1 worker). O risco existe só se o Start Command mudar para gunicorn multi-worker.

### 5.2 docker-compose.yml

Apenas `db` (pgvector/pgvector:pg16). **Sem Redis.**

### 5.3 Dependências (`pyproject.toml`)

- **Redis**: NÃO está nas dependencies.
- **langchain>=0.3 + langchain-openai>=0.3**: disponíveis.
- **httpx>=0.27**: disponível.
- **gunicorn>=26**: instalado, não usado pelo agente.
- **Sem tenacity** ou retry lib.
- **Alembic**: disponível, mas `alembic/versions/` vazio (migrações aplicadas fora do versionamento).

---

## 6. Prompts atuais — mapa de substituição

| Arquivo atual | Usado por | Situação na refatoração |
|---|---|---|
| `prompts/intencao.md` | `agents/classificador.py` | → `prompts/01-classificador.md` (10 rótulos + estado_pendente + histórico) |
| `prompts/sistema.md` | `agents/extrator.py` | Identidade → `00-base.md`; regras de extração → `02-extracao-cadastrar.md` |
| `prompts/categorizacao.md` | `agents/categorizador.py` | Absorvida pela injection de cadastro |
| `prompts/cadastro-confirmado.md` | `services/formatador.py` | → template Python (sem LLM) |
| `prompts/resumo.md` | `services/formatador.py` | → template Python (sem LLM) |
| `prompts/confirmacao.md` | `services/formatador.py` | → template Python (sem LLM) |
| `prompts/fora-de-escopo.md` | `services/formatador.py` | → template Python (menu padrão) |

**Prompts inline a eliminar/migrar:** `extrator_alteracao` → `03-extracao-atualizar.md`; `confirmacao_chain` → absorvido pelo classificador; `extrator_lista`/`filtro_consulta`/`extrator_parcelas`/`extrator_exclusao_lote` → absorvidos (classificador + extrações).

---

## 7. Pontos de integração e riscos

### 7.1 Acoplamento entre pacotes

`backend/` e `frontend/` **não importam nada** de `agent/`. Compartilham: `backend/models` + `backend/repositories` (importados in-process pelo agent), `.env` e o banco.

### 7.2 Embeddings existentes

Indexação atual: `"{tipo} {categoria} {descricao} {dd/mm/yyyy}"` — a spec mantém o mesmo formato ⇒ **sem re-embedding do histórico**. A correção é só no texto de **busca** (embedar a referência extraída, não a mensagem crua).

### 7.3 Migrações

`alembic/versions/` vazio. `DINHEIRO` no enum exigiria migração + alteração de `backend/models/enums.py` (fora do escopo declarado de `agent/`).

### 7.4 Limiares RAG

Limiar atual hardcoded `> 1.0` em 4 lugares (`alterar.py:63`, `excluir.py:50`, `marcar_pago.py:48`, `consultar.py:111`). Faixas novas devem vir de `Settings`.

---

## 8. Código reutilizável

### 8.1 Reusar sem mudança

| Arquivo | O quê |
|---|---|
| `agent/services/parcelas.py` | `adicionar_meses`, `status_por_data`, `data_status_por_forma`, `datas_do_grupo` |
| `agent/agents/base.py` | `coagir_data`, `carregar_prompt` (`criar_llm*` generalizar p/ Settings) |
| `agent/agents/embedder.py` | `Embedder` completo |
| `backend/repositories/dtos.py` | `TransacaoCreate`, `TransacaoUpdate`, `AgregadoCategoria` |
| `agent/services/cadastrar.py::_valores_das_parcelas` | Extrair para `parcelas.py` |

### 8.2 Reusar com adaptação

| Arquivo | Adaptação |
|---|---|
| `agent/services/confirmacao_state.py` | Vira implementação de `EstadoStore`; estado ganha `payload_pendente`, `campos_faltantes`, `opcoes`, `historico` |
| `agent/entrypoint/debounce.py` | `"\n".join`, lock, referência de task |
| `main.py::_SessionFactoryRepository` | Método novo p/ múltiplos candidatos com distância |
| `agent/integrations/evolution_client.py` | `raise_for_status` + retry |

### 8.3 Substituir completamente

`pipeline.py` → `roteador.py` · `formatador.py` → templates Python · `classificador.py` → 10 intenções/union · `extrator.py`+`categorizador.py` → tool cadastrar + injection · `confirmacao_chain.py` → eliminado · `marcar_pago.py` → tool atualizar · `consultar.py` → tool listar · `alterar.py` → tool atualizar · `excluir.py` → tool excluir · `filtro_consulta.py` → eliminado.

---

## 9. Riscos e perguntas abertas para o arquiteto

### Riscos técnicos

1. **`buscar_semantico_com_distancia` retorna sempre 1 resultado** (`.first()`). Zona ambígua exige método novo `buscar_semantico_multiplos_com_distancia(...) -> list[tuple[Transacao, float]]` — adição não-quebradora no repositório ou no adapter.
2. **`DINHEIRO` ausente em `FormaPagamentoEnum`** — exige migração + toque em `backend/` (fora do escopo declarado).
3. **`responsavel="Jhonatas"` hardcoded** em `dtos.py:31` (backend, intocável) e `extrator.py:20`. Tool Cadastrar deve preencher explicitamente via `Settings.RESPONSAVEL_PADRAO`.
4. **Sem `updated_at`** na tabela — diff de confirmação exibe só campos da query.
5. **Alembic sem histórico versionado** — qualquer migração nova precisa criar a base.
6. **TTL duplo no estado** (pendência 5min × histórico 24h) — decidir estrutura.

### Perguntas abertas

- **`EstadoStore`**: Redis (dep nova) ou Postgres (tabela+migração) ou in-memory (1 worker confirmado)?
- **Multiusuário no webhook**: mantém `WHATSAPP_ALLOWED_NUMBER` single-user ou lookup por `Usuario.telefone` (índice único condicional existe)?
- **Histórico de conversa**: onde vive, quem popula, qual TTL?
- **Dedup por `message_id`** (`data.key.id` do payload): onde guardar?
- **`AGENTE_USUARIO_EMAIL`**: remover default.
- **Limiares RAG**: valores iniciais via `Settings`, calibrar depois.
- **Fronteira `conversar`**: sem acesso ao banco (decidido na spec) — refletir no classificador.
