# Levantamento — Agente Conversacional Financeiro (`agent/`)

> Levantamento da estrutura atual, fluxo completo (mensagem → resposta), funcionamento
> interno (prompts e delegação) e pontos de má prática identificados.
> Data: 11/06/2026 · Escopo: exclusivamente o diretório `agent/` (+ `prompts/`, que ele consome).

---

## 1. Estrutura atual

```
agent/
├── config.py                      → Settings (pydantic-settings, .env)
├── db.py                          → helper de engine (não usado pelo fluxo principal)
├── entrypoint/
│   ├── main.py                    → FastAPI + lifespan: wiring manual de TODA a DI
│   ├── webhook.py                 → POST /webhook/mensagem (Evolution API)
│   └── debounce.py                → MessageDebouncer (10s por número)
├── integrations/
│   └── evolution_client.py        → EvolutionApiClient (httpx, envio de texto)
├── agents/                        → "chains" LLM (LangChain + structured output)
│   ├── base.py                    → criar_llm(), criar_llm_formatacao(), carregar_prompt(), coagir_data()
│   ├── classificador.py           → intenção (8 rótulos) — prompt em arquivo
│   ├── extrator.py                → extração de lançamento — prompt em arquivo
│   ├── categorizador.py           → categoria — prompt em arquivo
│   ├── extrator_alteracao.py      → campos a alterar — prompt INLINE
│   ├── extrator_parcelas.py       → nº de parcelas — prompt INLINE
│   ├── extrator_exclusao_lote.py  → filtros de exclusão — prompt INLINE
│   ├── extrator_lista.py          → lote de lançamentos — prompt INLINE (extenso)
│   ├── filtro_consulta.py         → filtros de consulta — prompt INLINE
│   ├── confirmacao_chain.py       → sim/não · parcela/grupo — prompt INLINE
│   └── embedder.py                → text-embedding-3-small (1536d)
└── services/
    ├── pipeline.py                → roteador central (estado > intenção)
    ├── confirmacao_state.py       → máquina de estados in-memory (TTL 5min)
    ├── cadastrar.py               → CadastrarService (+ lote, parcelas, recorrência)
    ├── alterar.py                 → AlterarService (busca semântica + confirmação)
    ├── excluir.py                 → ExcluirService (unitário, grupo, lote)
    ├── marcar_pago.py             → MarcarPagoService
    ├── consultar.py               → ConsultarService (mensal/semanal/grupo/geral)
    ├── formatador.py              → Formatador (gpt-4o formata resposta final)
    └── parcelas.py                → funções puras de data/status (sem LLM/DB)

prompts/                           → 7 arquivos .md (parte dos prompts; o resto é inline)
```

**Dependências externas:** OpenAI (gpt-4o-mini, gpt-4o, text-embedding-3-small),
Evolution API (WhatsApp), PostgreSQL + pgvector (via `backend/repositories`, compartilhado in-process).

---

## 2. Fluxo completo: da mensagem ao output

### 2.1 Recepção (`entrypoint/webhook.py`)

1. Evolution API faz `POST /webhook/mensagem` com o evento.
2. Filtros silenciosos (sempre retornam `200 {"status": "ok"}`):
   - evento ≠ `messages.upsert` → descarta
   - `fromMe = true` → descarta (anti-loop)
   - número ≠ `WHATSAPP_ALLOWED_NUMBER` → descarta (single-user)
   - sem texto (`conversation` / `extendedTextMessage.text`) → descarta
3. Mensagem válida → `debouncer.receber(numero, texto, callback)`.

### 2.2 Debounce (`entrypoint/debounce.py`)

- Buffer por número; cada mensagem nova reinicia um timer de **10 segundos**.
- Ao disparar, concatena o buffer com **espaço** (`" ".join`) e agenda
  `_processar_e_responder(numero, texto)` via `asyncio.ensure_future`.

### 2.3 Processamento (`main.py::_processar_e_responder` → `Pipeline.processar`)

```
texto ─→ ConfirmacaoState.obter(numero)
          │
          ├─ estado pendente? ─→ _rotear_estado          (NÃO chama o classificador)
          │     AGUARDAR_PARCELAS   → ExtratorParcelas → cadastrar.executar_com_parcelas_confirmadas
          │     AGUARDAR_RECORRENCIA→ ConfirmacaoChain(sim_nao) → cadastrar.executar_com_recorrencia_confirmada
          │     EXCLUIR_LOTE        → ConfirmacaoChain(sim_nao) → excluir.confirmar_lote
          │     ALTERAR             → ConfirmacaoChain(sim_nao) → alterar.confirmar
          │     MARCAR_PAGO         → ConfirmacaoChain(sim_nao) → marcar_pago.confirmar
          │     EXCLUIR             → ConfirmacaoChain(sim_nao | escopo_parcela) → excluir.confirmar
          │
          └─ sem estado ─→ Classificador (gpt-4o-mini) ─→ _rotear_intencao
                CADASTRAR       → CadastrarService.executar
                CADASTRAR_LOTE  → CadastrarService.executar_lote (ExtratorLista)
                ALTERAR         → AlterarService.iniciar
                MARCAR_PAGO     → MarcarPagoService.iniciar
                EXCLUIR         → ExcluirService.iniciar
                EXCLUIR_LOTE    → ExcluirService.iniciar_lote (ExtratorExclusaoLote)
                CONSULTAR       → ConsultarService.executar (FiltroConsulta)
                FORA_DE_ESCOPO  → Formatador("fora_escopo")
```

### 2.4 Exemplo do caminho mais comum (CADASTRAR)

1. `Extrator.extrair(msg, hoje)` — **LLM #1** (gpt-4o-mini, structured output `ExtracaoResult`).
2. Se `menciona_cartao` e sem parcelas → salva estado `AGUARDAR_PARCELAS` e pergunta. (fluxo pausa)
3. `Categorizador.categorizar(...)` — **LLM #2** (pula se RECEITA/INVESTIMENTO).
4. Se categoria GASTOS_FIXOS sem parcela → estado `AGUARDAR_RECORRENCIA` e pergunta. (pausa)
5. `_processar`: toda a matemática em **Python/Decimal** — valores de parcela
   (resto na última), datas (+1 mês para crédito/boleto, dia clampado), status
   (PAGO/PENDENTE por data e forma), `grupo_parcela_id` (UUID único por grupo).
6. `Embedder.gerar_para_transacao` — **LLM #3** (embedding `"{tipo} {categoria} {descricao} {dd/mm/yyyy}"`, nunca inclui valor).
7. `repository.criar_lote(...)` — persiste 1 linha por parcela (mesmo embedding).
8. `Formatador.formatar(resultado, "cadastro")` — **LLM #4** (gpt-4o temp=0.3, serializa o
   resultado em texto chave-valor e pede formatação WhatsApp via `cadastro-confirmado.md`).

→ **4 chamadas de API sequenciais** no caminho feliz de um cadastro simples.

### 2.5 Saída

`main.py::_processar_e_responder` → `EvolutionApiClient.enviar_mensagem(numero, resposta)`
(`POST /message/sendText/{instance}`). Qualquer exceção no caminho é capturada,
logada — e **o usuário não recebe nada**.

---

## 3. Como o agente trata prompts e delega atividades

### 3.1 Modelo de delegação

Não há um "agente" no sentido de loop autônomo com tools. A arquitetura é um
**pipeline determinístico de chains especializadas**:

- Cada "agent" em `agent/agents/` é uma classe fina: `criar_llm().with_structured_output(PydanticModel)`
  + um system prompt + um método `async`. O LLM **nunca decide o fluxo** — apenas
  preenche um schema Pydantic.
- O roteamento é 100% código Python (`Pipeline` com cadeias de `if`), guiado pelo
  rótulo do `Classificador` ou pelo estado pendente da `ConfirmacaoState`.
- Regra de ouro respeitada: **matemática nunca vai pro LLM** (Decimal em services),
  e o LLM de formatação recebe valores já calculados com instrução de não recalcular.

### 3.2 Gestão de prompts — DOIS regimes coexistindo

| Regime | Onde | Chains |
|--------|------|--------|
| Arquivo `.md` em `prompts/` via `carregar_prompt()` | versionável, legível | `classificador` (intencao.md), `extrator` (sistema.md), `categorizador` (categorizacao.md), `formatador` (cadastro-confirmado, resumo, confirmacao, fora-de-escopo) |
| String inline hardcoded no `__init__`/método | invisível, duplicada | `extrator_alteracao`, `extrator_parcelas`, `extrator_exclusao_lote`, `extrator_lista` (~20 linhas de regras de negócio!), `filtro_consulta`, `confirmacao_chain` |

Consequências: as **regras de categorização existem em dois lugares**
(`categorizacao.md` e o prompt inline do `extrator_lista`) e já divergem;
`sistema.md` mistura identidade global com regras de extração; os prompts `.md`
têm seções "Saída esperada ```json" que são redundantes com structured output.

### 3.3 Modelos LLM

- `gpt-4o-mini` temp=0 → classificar/extrair/categorizar (hardcoded em `base.py`).
- `gpt-4o` temp=0.3 → formatação final (hardcoded).
- `text-embedding-3-small` → busca semântica (limiar de distância L2 `> 1.0` = "não achei",
  decidido no service).

---

## 4. Pontos de má prática identificados

### 🔴 Críticos (correção prioritária)

1. **Webhook sem autenticação** (`webhook.py`). Qualquer um que descubra a URL pode
   POSTar um payload com o `remoteJid` do número autorizado e **cadastrar/alterar/excluir
   transações em nome do usuário**. O único "controle" é um campo do próprio payload.
   → Validar apikey/assinatura da Evolution API (header) ou token secreto na URL.

2. **Estado pendente sequestra qualquer mensagem** (`pipeline.py:36`,
   `confirmacao_chain.py`). Com estado ativo, *qualquer* texto vai para a
   `ConfirmacaoChain`, cujo schema `Literal["sim","nao","parcela","grupo"]` **força**
   uma resposta mesmo para mensagem sem relação ("gastei 30 no uber" durante um
   EXCLUIR_LOTE pendente pode virar "sim" e **apagar registros em massa**).
   O prompt `confirmacao.md` até manda "cancelar e processar a nova mensagem
   normalmente", mas **o código não implementa isso**. → Adicionar rótulo
   `"outro"`/escape no schema e reclassificar a intenção quando ocorrer.

3. **Erro = silêncio total para o usuário** (`main.py:196`). `except Exception` só
   loga; o usuário fica sem resposta e sem saber se o gasto foi registrado.
   → Enviar mensagem de erro amigável no `except` (best effort).

4. **Estado e debounce in-memory + gunicorn**. `ConfirmacaoState`, `MessageDebouncer`
   e os timers vivem no processo. O Dockerfile recém-adicionado usa **gunicorn**:
   com >1 worker, a confirmação pode chegar em outro worker e o fluxo quebra
   aleatoriamente. → Fixar 1 worker (documentado) ou mover estado para
   Postgres/Redis.

5. **Dados pessoais hardcoded no código**:
   - `extrator.py:20` — `responsavel: str = "Jhonatas"` como default do *schema de extração*.
   - `config.py:13` — `AGENTE_USUARIO_EMAIL` com default do email pessoal (contradiz o commit a62e576 que limpou os exemplos).
   → Mover para configuração obrigatória, sem default.

### 🟡 Importantes

6. **Debounce concatena com espaço e perde quebras de linha** (`debounce.py:18`).
   A detecção de `CADASTRAR_LOTE` depende de "vários itens separados por quebra de
   linha" (`intencao.md`) — duas mensagens viram uma linha só e o lote degrada para
   cadastro simples. → `"\n".join`. Além disso `asyncio.ensure_future` sem guardar
   referência (task pode ser coletada pelo GC) e sem lock.

7. **Sem idempotência de webhook**. O `message.id` do payload é ignorado; retry da
   Evolution API duplica lançamentos. → Dedup por id de mensagem (TTL curto).

8. **`confianca` do classificador é ignorada** (`pipeline.py`). O prompt promete
   "quando baixa, pedir esclarecimento", mas o pipeline nunca lê o campo —
   contrato do prompt sem implementação.

9. **Re-extração desnecessária e cara** (`cadastrar.py:117-134`). Ao confirmar
   parcelas/recorrência, a mensagem original é **re-enviada ao LLM** em vez de
   guardar a `ExtracaoResult` no `EstadoConfirmacao`. Custo dobrado e risco de
   extração divergente entre a pergunta e a confirmação.

10. **LLM de chamada em chamada sem timeout/retry**. Nenhuma chain tem
    `max_retries`/timeout configurado; uma falha da OpenAI vira exceção genérica →
    silêncio (item 3). O `Formatador` tem `except Exception` largo que mascara
    qualquer erro como "Não foi possível formatar".

11. **gpt-4o para formatar dados já prontos** (`formatador.py`). Toda resposta de
    cadastro/consulta paga uma chamada do modelo mais caro com temp=0.3 — que pode
    **alterar os números** que o template manda exibir. O `cadastro_lote` já é
    formatado 100% em Python; o resto poderia seguir o mesmo caminho (template
    determinístico), reservando LLM só para o `fora_escopo`/conversação.

12. **Embedding de busca poluído** (`alterar/excluir/marcar_pago.iniciar`). A busca
    embeda a mensagem **crua** ("apaga o gasto do uber de ontem") enquanto o
    armazenamento embeda `"{tipo} {categoria} {descricao} {data}"` — verbos de
    comando entram no vetor e degradam o match. → Extrair a referência ao registro
    antes de embedar (ou normalizar o texto de busca).

13. **Duplicação tripla**: `_formatar_card` + `_NAO_ENCONTRADO` + limiar `1.0`
    copiados em `alterar.py`, `excluir.py` e `marcar_pago.py` (e o limiar também em
    `consultar.py`). → Extrair para módulo comum (ex.: `services/busca.py`).

14. **`Categorizador` burla a própria validação** (`categorizador.py:18`).
    `model_construct(categoria="INVESTIMENTO")` injeta um valor **fora do `Literal`**
    do schema — gambiarra que quebra a confiança no contrato Pydantic.

15. **`AlterarService.iniciar` gasta LLM antes de saber se há registro**
    (`alterar.py:57-64`): extrai os novos dados e só depois busca; se não achar,
    a extração foi desperdiçada. Além disso `nova_categoria: str | None` é texto
    livre — pode gravar categoria inválida no banco (sem `Literal`/Enum).

### 🟢 Menores / dívidas

16. **Prompts inline vs. arquivo** (seção 3.2) — consolidar tudo em `prompts/`
    e remover as regras duplicadas de categorização do `extrator_lista`.
17. **`logging.basicConfig` no módulo do webhook** + `import logging` dentro de
    função em `main.py`; e o webhook loga o **payload inteiro** (PII: número,
    conteúdo da mensagem) em INFO.
18. **`date.today()` espalhado** (cadastrar, consultar, excluir, pipeline) — usa o
    fuso do servidor; container em UTC registra "ontem/hoje" errado à noite
    (BRT = UTC-3). → Relógio injetável com timezone do usuário.
19. **`EvolutionApiClient` não checa status HTTP** (sem `raise_for_status`) e engole
    exceção — envio falho parece sucesso.
20. **Modelos hardcoded em `base.py`** — nome/temperatura deveriam vir de `Settings`
    para permitir troca sem deploy.
21. **`FiltroConsulta` suporta `"dinamico"`/`periodo_inicio/fim` mas o
    `ConsultarService` não implementa** — cai no `else` geral. Schema promete o que
    o código não entrega (e `resumo.md` menciona "filtros dinâmicos").
22. **Sem observabilidade de LLM**: nenhum log de tokens/custo/latência por chain,
    nenhum tracing (LangSmith ou equivalente).
23. **`agent/db.py` aparentemente morto** no fluxo do agente (o wiring usa
    `create_async_engine` direto no `main.py`) — confirmar e remover ou usar.

### Sobre o propósito declarado ("apoiar decisões financeiras")

O agente hoje é um **CRUD conversacional**: registra, altera, exclui e soma. Não há
nenhuma capacidade consultiva (análise de tendência, alertas de orçamento, comparação
entre meses, sugestões) nem **memória conversacional** — cada mensagem é processada
isolada (exceto a máquina de confirmação). Qualquer pergunta de aconselhamento cai em
`FORA_DE_ESCOPO` e recebe o menu. Se a visão de produto é "copiloto financeiro",
falta uma intenção `ACONSELHAR`/`ANALISAR` com contexto histórico do usuário.

---

## 5. Resumo das melhorias sugeridas (ordem de ataque)

| # | Melhoria | Severidade | Esforço |
|---|----------|-----------|---------|
| 1 | Autenticar o webhook (apikey/assinatura Evolution) | 🔴 | baixo |
| 2 | Escape na ConfirmacaoChain (rótulo "outro" → reclassificar) | 🔴 | baixo |
| 3 | Responder o usuário em caso de erro | 🔴 | baixo |
| 4 | Estratégia p/ estado in-memory × gunicorn (1 worker ou Redis/PG) | 🔴 | médio |
| 5 | Remover dados pessoais hardcoded (responsavel, email) | 🔴 | baixo |
| 6 | Debounce com `\n` + referência da task + dedup por message.id | 🟡 | baixo |
| 7 | Guardar extração no estado (não re-extrair na confirmação) | 🟡 | baixo |
| 8 | Timeout/retry nas chains + usar `confianca` baixa | 🟡 | médio |
| 9 | Formatação determinística (template Python) p/ cadastro/consulta | 🟡 | médio |
| 10 | Normalizar texto de busca semântica (alterar/excluir/pagar) | 🟡 | médio |
| 11 | Extrair módulo comum de busca/card (eliminar duplicação tripla) | 🟡 | baixo |
| 12 | Consolidar todos os prompts em `prompts/` (fonte única) | 🟢 | baixo |
| 13 | Timezone do usuário p/ datas + relógio injetável | 🟢 | médio |
| 14 | Observabilidade LLM (tokens, latência, tracing) | 🟢 | médio |
| 15 | Visão de produto: intenção consultiva/analítica com histórico | 🟢 | alto |
