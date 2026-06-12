# Plano Técnico — melhorias-agente

**Status:** Aprovado
**Spec:** `specs/melhorias-agente/sugestao-melhoria.md` (v1.1, consolidada com o humano)
**Documentos de comportamento:** `classificador.md`, `fluxo-atendimento-{cadastro,lista,atualizar,excluir}.md`, `readme.md`, `prompt-base.md`
**Exploração:** `specs/melhorias-agente/exploracao.md`
**Contratos:** `intencao-schema.md`, `estado-store.md`, `resultado-tools.md`, `rag-busca.md`, `webhook-fila.md`, `prompts-injection.md`, `relogio-contexto.md` (todos a Congelar antes de qualquer task de implementação)

> Gate humano obrigatório: nada de implementação enquanto este `plan.md` estiver `Rascunho`.
> A implementação só começa quando um humano marcar `Status: Aprovado`.

---

## 1. Objetivo

Refatoração estrutural **dentro de `agent/`** que troca o pipeline atual de chains acopladas (4 chamadas LLM no caminho comum, formatação por gpt-4o, estado que sequestra mensagens, webhook sem auth) por uma arquitetura determinística:

```
Webhook (auth + dedup) → Fila por usuário → Worker (micro-debounce \n) →
Classificador (LLM #1, union tipada) → Roteador (Python puro) →
Tool (cadastrar/listar/atualizar/excluir/conversar) → Formatador (templates Python) → WhatsApp
```

Meta: **≤ 2 chamadas LLM** por mensagem (1 classificador + no máximo 1 extração/verbalização). `backend/` e `frontend/` **intocados** (única exceção avaliada: `DINHEIRO` no enum — ver Decisão D3, **adiada**).

---

## 2. Arquitetura-alvo

### 2.1 Pacotes de `agent/` após a refatoração

```
agent/
├── config.py                  # Settings + RESPONSAVEL_PADRAO, modelos LLM, limiares RAG, WEBHOOK_APIKEY, TZ
├── domain/
│   ├── intencao.py            # Intencao + ParametrosPorAcao (union discriminada)  [contrato intencao-schema]
│   └── estado.py              # EstadoConversa, OpcaoPendente, Mensagem            [contrato estado-store]
├── entrypoint/
│   ├── main.py                # FastAPI + wiring (lifespan)
│   ├── webhook.py             # auth (apikey) + extrai + dedup + enfileira → 200   [contrato webhook-fila]
│   └── worker.py              # consumer da fila + micro-debounce (\n)             [contrato webhook-fila]
├── services/
│   ├── classificador.py       # LLM → Intencao                                     [contrato intencao-schema + prompts-injection]
│   ├── roteador.py            # match acao → Tool (+ guarda de pendência)          [contrato resultado-tools]
│   ├── formatador.py          # ResultadoTool → string WhatsApp (templates Python) [contrato resultado-tools]
│   ├── estado_store.py        # EstadoStore (interface) + Redis + Memoria(testes)  [contrato estado-store]
│   ├── rag.py                 # BuscaRAG (3 faixas)                                [contrato rag-busca]
│   ├── prompts.py             # montar_prompt(acao, contexto) (base + injection)   [contrato prompts-injection]
│   └── relogio.py             # Relogio (now() com TZ do usuário, injetável)       [contrato relogio-contexto]
├── tools/
│   ├── cadastrar.py           # itens → registros montados (Decimal, parcelas)     [resultado-tools]
│   ├── listar.py              # filtros → agregação SQL + agrupamento visual       [resultado-tools]
│   ├── atualizar.py           # referência → RAG → diff/propagação                 [resultado-tools + rag-busca]
│   ├── excluir.py             # referência/filtros → RAG/count → escopo            [resultado-tools + rag-busca]
│   └── conversar.py           # LLM verbaliza (sem banco)                          [resultado-tools + prompts-injection]
├── integrations/
│   └── evolution_client.py    # + raise_for_status + retry
├── agents_llm.py              # helpers criar_llm()/embedder a partir de Settings  (ex-agents/base.py)
└── prompts/                   # 00-base, 01-classificador, 02-extracao-cadastrar, 03-extracao-atualizar, 06-conversar

backend/                       # INTOCADO (exceto método aditivo no repository — ver D2)
frontend/                      # INTOCADO
```

### 2.2 Reuso confirmado (exploração §8)

| Origem atual | Destino |
|---|---|
| `agent/services/parcelas.py` (funções puras testadas) | mantido como `agent/tools/_parcelas.py` (posse da task de cadastrar) — `adicionar_meses`, `status_por_data`, `data_status_por_forma`, `datas_do_grupo` + `valores_das_parcelas` extraído de `cadastrar.py` |
| `agent/agents/base.py::carregar_prompt/coagir_data/criar_llm*` | `agent/agents_llm.py` (modelos via Settings) |
| `agent/agents/embedder.py::Embedder` | reusado pelo RAG e por cadastrar |
| `agent/services/confirmacao_state.py` | vira `EstadoStoreMemoria` (testes/dev); produção usa `EstadoStoreRedis` |
| `agent/entrypoint/debounce.py` | absorvido por `worker.py` (`\n`, lock, referência de task) |
| `backend/repositories/dtos.py` | reusado sem mudança (`TransacaoCreate/Update`, `AgregadoCategoria`) |

### 2.3 Caminho LLM por mensagem (meta)

- `cadastrar`/`atualizar` complexos: 1 classificador + 1 extração especializada = **2**
- `listar`/`excluir`/`confirmar`/`cancelar`/`selecionar`/`complementar`/`desconhecida`: **1** (só classificador; parâmetros saem dele)
- `conversar`: 1 classificador + 1 verbalização = **2**
- `confirmar` que persiste: **0** chamadas extras (payload já montado no estado)

---

## 3. Decisões (com justificativa)

### D1 — `EstadoStore` v1: **Redis** atrás de interface *(decisão do humano no gate)*

Decisão do humano: usar Redis. **`EstadoStoreRedis`** (`redis.asyncio`, pacote `redis>=5`) como implementação de produção, atrás da interface **async** `EstadoStore` (contrato `estado-store.md`); **`EstadoStoreMemoria`** mantida para testes/dev — ambas passam a mesma suíte de comportamento. Serialização: `EstadoConversa` como JSON (chave `estado:{usuario_id}`, TTL físico 24h); a expiração **lógica** (pendência 5 min × histórico 24h) continua decidida em `obter` contra `agora` injetado. Infra: dependência `redis>=5` no `pyproject.toml`, serviço `redis` no `docker-compose.yml`, config `REDIS_URL` em `Settings`. Ganhos: estado sobrevive a restart e fica pronto para multi-worker. **Invariante "1 worker" permanece** por causa da fila/micro-debounce in-process do worker (não distribuídos nesta feature). Testes com cliente Redis mockado (`AsyncMock`) — sem Redis real, convenção do repo.

### D2 — Múltiplos candidatos com distância **sem quebrar `TransacaoRepository`**

Risco 1 da exploração: `buscar_semantico_com_distancia` faz `.first()` e devolve 1 só. As 3 faixas do RAG precisam de 2+ candidatos com distância. Decisão: **adicionar método aditivo** `buscar_semantico_multiplos_com_distancia(embedding, limite, usuario_id) -> list[tuple[Transacao, float]]` em `backend/repositories/transacao_repository.py` — **adição não-quebradora** (nenhuma assinatura existente muda; é a única exceção permitida ao "backend intocado", justificada porque (a) é a fronteira de dados, (b) o método atual tem o bug documentado de ignorar `limite`, (c) replicar SQL pgvector no `agent/` violaria a camada). O adapter `_SessionFactoryRepository` (em `main.py`) ganha o passthrough correspondente. `agent/tools` e `rag.py` consomem **só** este método novo; o antigo permanece para o uso single-result.

### D3 — `DINHEIRO` no `FormaPagamentoEnum`: **adiar**

Incluir agora exige migração Alembic (base inexistente) + alteração de `backend/models/enums.py` — fora do escopo declarado e fora da fronteira de `agent/`. Decisão: **adiar**. O `00-base.md` lista `DINHEIRO` como forma válida na linguagem, mas a Tool Cadastrar **mapeia `DINHEIRO → PIX`** (à vista/PAGO, mesmo comportamento financeiro) com `detalhes="dinheiro"` opcional, até que uma feature dedicada faça a migração. Registrado como dívida. (Se o humano reabrir, vira uma task isolada `backend` + migração — não está neste plano.)

### D4 — Estratégia de migração: **big-bang dentro de `agent/`, com camada de dados preservada**

A spec é explicitamente "refatoração estrutural, não correções pontuais". `backend/repositories`/`backend/models` ficam; tudo em `agent/services` (pipeline, formatador, chains antigas) e `agent/agents/*` é **substituído**. Para não deixar a árvore quebrada no meio do caminho, a substituição é **incremental por camada** no DAG (domínio → infra → tools → roteador/worker → integração), mas o resultado final remove os módulos antigos de uma vez na **task de limpeza/integração** (T11). Os testes antigos (`test_pipeline.py`, `test_service_*`) são **removidos/reescritos conscientemente** nessa task — declarado explicitamente para não restar teste órfão importando módulo apagado.

### D5 — Divisão de extração: **classificador extrai o básico; extração especializada (chamada 2) só para cadastrar/atualizar**

O classificador (`classificador.md`) já extrai os parâmetros simples por ação (itens com descrição/valor/parcela, referência+campo+novo_valor, período/categoria, opção, campo+valor de complemento). **Não há 2ª chamada** para `listar`/`excluir`/`conversar`-roteamento. A extração especializada (LLM #2, prompts `02-extracao-cadastrar.md`/`03-extracao-atualizar.md`) é acionada **apenas** quando a Tool Cadastrar/Atualizar precisa de categorização ou de campos que o classificador deixou ambíguos. **Categorização** entra na injection de cadastrar (não há chain `categorizador` separada). Na prática: cadastro simples e bem-formado pode resolver categoria por regra; cadastro/atualização ricos chamam a extração especializada uma vez. O `confirmar` **nunca** re-extrai (corrige o bug de re-extração custosa, levantamento §9): persiste o `payload_pendente` já montado.

### D6 — Histórico de conversa: **na própria `EstadoConversa`, populado pelo worker**

Estrutura: `historico: list[Mensagem]` (`Mensagem = {papel: "usuario"|"assistente", texto: str, em: datetime}`), **últimas N=5** mensagens (ring buffer). Populado pelo **worker** após processar: registra a mensagem do usuário (já agrupada pelo debounce) e a resposta enviada. TTL do histórico = **24h** (separado do TTL de 5 min da pendência). O classificador recebe `{historico_recente}` formatado e `{estado_pendente}` (resumo textual da pendência) — sem isso, "confirmar"/"2"/"foi 350" são inclassificáveis (spec §3.3).

### D7 — Autenticação do webhook: **header `apikey` da Evolution API**

A Evolution API envia o header `apikey` nos webhooks; valor configurável. Decisão: nova config **`WEBHOOK_APIKEY`** (obrigatória, sem default) comparada por igualdade constante-time com o header `apikey` da requisição; ausência/divergência → **401** (não 200 silencioso). Mantém-se o filtro `WHATSAPP_ALLOWED_NUMBER` para single-user (v1) — lookup por `Usuario.telefone` fica como ponto de extensão (não nesta feature). `AGENTE_USUARIO_EMAIL` **perde o default hardcoded** (vira obrigatório).

### D8 — Confirmação persiste payload pronto (decisão do produto, já tomada)

Toda escrita (cadastrar/atualizar/excluir) passa por confirmação. A Tool monta o(s) registro(s)/diff/escopo e devolve `status="aguardando_confirmacao"` com o **payload já montado** guardado em `EstadoConversa.payload_pendente`. O `confirmar` no roteador **persiste sem LLM**. Intenção operacional nova com pendência ativa **cancela** a pendência (regra de ouro, spec §3.4) — elimina o sequestro de mensagem.

### D9 — Parcelado: só atual + futuras; status da atual por data de vencimento (decisão do produto, já tomada)

Reusa `agent/services/parcelas.py`. Gera parcela atual e futuras (anteriores **não** cadastradas), mesmo `grupo_parcela_id`, valor da parcela repetido, dia preservado avançando o mês. Status da atual: `status_por_data` sobre o vencimento. Embedding mantém o formato atual (`"{tipo} {categoria} {descricao} {dd/mm/yyyy}"`) — sem re-embedding do histórico (exploração §7.2).

### D10 — Formatador 100% templates Python; LLM só em `conversar`

Nenhum número passa por LLM. Templates vivem em `agent/services/formatador.py` (strings Python derivadas dos `fluxo-atendimento-*.md`). `conversar` é a única resposta em linguagem natural — vem já pronta da Tool.

---

## 4. Tarefas (DAG)

Todas stack **python**. Contratos a Congelar primeiro (T00); nenhuma task de implementação depende de fronteira em rascunho. Tarefas paralelas **não compartilham arquivos** (inclusive de teste).

| ID | Tarefa | Stack | Depende de | Paralelizável com |
|----|--------|-------|-----------|-------------------|
| T00 | Congelar os 7 contratos (gate de fronteira) | — | plan aprovado | — |
| T01 | `domain/intencao.py` — `Intencao` + `ParametrosPorAcao` (union) | python | T00 | T02, T03, T04 |
| T02 | `domain/estado.py` + `services/estado_store.py` (interface + `EstadoStoreMemoria`) | python | T00 | T01, T03, T04 |
| T03 | `services/relogio.py` + `config.py` (novas Settings) | python | T00 | T01, T02, T04 |
| T04 | Repository: método aditivo `buscar_semantico_multiplos_com_distancia` + passthrough no adapter | python | T00 | T01, T02, T03 |
| T05 | `prompts/*` (00-base + injections) + `services/prompts.py` (montagem) | python | T00 | T01, T02, T03, T04 |
| T06 | `services/classificador.py` (LLM → Intencao) | python | T01, T03, T05 | T07, T08 |
| T07 | `services/rag.py` (BuscaRAG 3 faixas) | python | T03, T04 | T06, T08 |
| T08 | `tools/cadastrar.py` + `tools/_parcelas.py` (reuso + valores_das_parcelas) | python | T01, T02, T03, T05 | T06, T07, T09, T10 |
| T09 | `tools/listar.py` | python | T01, T03, T04 | T07, T08, T10, T11 |
| T10 | `tools/atualizar.py` + `tools/excluir.py` | python | T01, T02, T03, T07 | T08, T09 |
| T11 | `tools/conversar.py` | python | T01, T05 | T08, T09, T10 |
| T12 | `services/formatador.py` (templates Python das 5 tools + menu) | python | T01 (resultado-tools) | T06, T07, T08, T09, T10, T11 |
| T13 | `services/roteador.py` (match + guarda de pendência + confirmar sem LLM) | python | T06, T08, T09, T10, T11, T12 | — |
| T14 | `entrypoint/webhook.py` + `entrypoint/worker.py` (auth, dedup, fila, debounce `\n`) | python | T02, T13 | — |
| T15 | `integrations/evolution_client.py` (raise_for_status + retry) | python | T00 | T06–T12 |
| T16 | Integração + limpeza: `main.py` (wiring), remover módulos antigos de `agent/`, reescrever/remover testes antigos, `db.py` morto | python | T13, T14, T15 | — |

### DAG (texto)

```
plan Aprovado
  → T00 (congela 7 contratos)
       ├→ T01 (intencao)        ┐
       ├→ T02 (estado/store)    │ camada de domínio/infra (paralelas, arquivos disjuntos)
       ├→ T03 (relogio/config)  │
       ├→ T04 (repo método)     │
       ├→ T05 (prompts)         │
       └→ T15 (evolution client)┘
            T01,T03,T05 → T06 (classificador)
            T03,T04     → T07 (rag)
            T01,T02,T03,T05 → T08 (cadastrar)
            T01,T03,T04 → T09 (listar)
            T01,T02,T03,T07 → T10 (atualizar+excluir)
            T01,T05     → T11 (conversar)
            T01         → T12 (formatador)
       T06,T08,T09,T10,T11,T12 → T13 (roteador)
       T02,T13                 → T14 (webhook+worker)
       T13,T14,T15             → T16 (integração + limpeza)
```

### Janelas de paralelismo

- **Onda 1 (após T00):** T01, T02, T03, T04, T05, T15 — seis tasks, zero arquivos em comum.
- **Onda 2:** T06, T07, T08, T09, T10, T11, T12 — cada uma toca só os seus arquivos (e seu teste próprio).
- **Onda 3:** T13.
- **Onda 4:** T14.
- **Onda 5:** T16 (serial, integra e limpa).

---

## 5. Ordem de integração

1. **T00** congela contratos (gate). Nada de implementação antes.
2. Mergear **Onda 1** (T01–T05, T15). `uv run pytest tests/ -v` verde após cada uma (testes novos isolados; os antigos ainda existem e devem continuar passando até T16).
3. Mergear **Onda 2** (T06–T12). Cada Tool/serviço com seu teste.
4. **T13** (roteador) integra as tools sob os contratos.
5. **T14** (webhook+worker) liga a borda HTTP à fila/worker.
6. **T15** já mergeado na Onda 1; reverificar.
7. **T16** por último: re-wire `main.py`, **remove** `agent/services/{pipeline,confirmacao_state,cadastrar,alterar,excluir,marcar_pago,consultar,formatador}.py`, `agent/agents/{classificador,extrator,categorizador,extrator_*,filtro_consulta,confirmacao_chain}.py`, `agent/entrypoint/debounce.py`, `agent/db.py` (morto), prompts órfãos; **reescreve/remove** `tests/test_pipeline.py`, `tests/test_service_cadastrar.py`, `tests/test_service_alterar_excluir.py` (migram para os testes por-tool); preserva/atualiza `tests/test_parcelas_helper.py` (apontando para `agent/tools/_parcelas.py`); atualiza `tests/test_webhook.py` para a nova auth/fila. Critério: `grep` sem import de módulo removido.
8. Verificação total da feature (§7).

---

## 6. Riscos

- **R1 — Dependência nova de infra: Redis (D1).** Agente não sobe sem Redis acessível (`REDIS_URL`). Mitigação: serviço no `docker-compose.yml`, falha explícita de config, `EstadoStoreMemoria` como fallback de desenvolvimento. A fila/debounce continuam in-process — invariante "1 worker" documentada em `config.py`/README.
- **R2 — Método novo no repository (D2) é toque em `backend/`.** Mitigação: estritamente aditivo, coberto por teste, não muda assinatura existente; é a única exceção e está justificada como fronteira de dados.
- **R3 — `confianca` de LLM mal calibrada (spec §3.3).** Corte `< 0.7 → desconhecida` pode oscilar. Mitigação: limiar via `Settings`; bandas `Literal["alta","media","baixa"]` como plano B documentado no contrato `intencao-schema`.
- **R4 — Limiares RAG (3 faixas) sem dados reais.** Mitigação: faixas em `Settings` (`RAG_PISO`, `RAG_AMBIGUO`), calibrar depois; contrato `rag-busca` fixa só a semântica das faixas.
- **R5 — `responsavel="Jhonatas"` hardcoded em `dtos.py` (backend, intocável).** Mitigação: Tool Cadastrar **sempre** preenche `responsavel` explicitamente com `Settings.RESPONSAVEL_PADRAO` antes de criar o `TransacaoCreate` (nunca confia no default do DTO).
- **R6 — Sem `updated_at` na tabela.** Diff de confirmação do Atualizar exibe só os campos vindos da query (sem timestamp de edição). Aceito; não bloqueia.
- **R7 — `DINHEIRO` ausente (D3 adiado).** Mapeado para PIX; se relatórios precisarem distinguir, abrir feature dedicada.
- **R8 — Remoção de módulos antigos quebra imports/testes.** Mitigação: T16 serial, com `grep` de imports órfãos como critério de aceite.
- **R9 — Dedup de `message_id` in-memory cresce sem bound.** Mitigação: dict com TTL curto (ex. 10 min) e poda; suficiente para retry da Evolution.
- **R10 — Erro = silêncio (bug atual crítico).** O worker **sempre** envia mensagem de falha amigável no `except` (best-effort) — coberto em T14.

---

## 7. Verificação da feature

```bash
uv run pytest tests/ -v
```

Critérios de aceite da feature inteira:

- [ ] Todos os testes verdes; **nenhum** teste importa módulo removido (`grep -r "agent.services.pipeline\|confirmacao_chain\|agent.db" tests/` vazio).
- [ ] Classificador devolve `Intencao` tipada para as 10 intenções (cobertura dos exemplos de `classificador.md`).
- [ ] Cadastro simples: 1 classificador + 0/1 extração; `confirmar` persiste **sem** nova chamada LLM (mock de LLM não é chamado no caminho de confirmação).
- [ ] Parcelado gera só atual + futuras, mesmo `grupo_parcela_id`, status da atual por vencimento.
- [ ] Listar: agregação determinística, seção visual PARCELAMENTOS, split pago/pendente em `Decimal`, **zero** LLM.
- [ ] Atualizar/Excluir: RAG com 3 faixas (match/ambíguo/piso); propagação para futuras em valor/data; escopo numerado na exclusão de parcelado.
- [ ] Intenção nova durante pendência **cancela** a pendência (sem "sim" forçado).
- [ ] Webhook: header `apikey` inválido → 401; dedup por `message_id` evita duplicar; debounce junta fragmentos com `\n`.
- [ ] Erro no processamento → usuário recebe mensagem de falha (nunca silêncio).
- [ ] `conversar` não acessa o banco (repository não é chamado no caminho de conversar).
- [ ] Datas usam TZ `America/Sao_Paulo` via relógio injetável.
