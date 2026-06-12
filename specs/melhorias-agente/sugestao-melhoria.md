# Especificação — Agente Financeiro WhatsApp

**Versão:** 1.1 (consolidada após revisão técnica)
**Stack:** LangChain · Python 3.12 · FastAPI · Redis (ou Postgres, ver §7) · PostgreSQL + pgvector
**Canal:** WhatsApp via Evolution API

---

## 1. Visão Geral

O agente financeiro é um sistema conversacional que opera via WhatsApp, permitindo ao usuário cadastrar, consultar, atualizar e excluir registros financeiros em linguagem natural.

O design prioriza **simplicidade operacional**: LLM apenas onde há ambiguidade de linguagem natural (classificar, extrair, conversar). Todo o resto — regras de negócio, matemática, formatação de resposta — é **código determinístico** (Python + `Decimal` + template string).

Esta versão é uma **refatoração estrutural** do `agent/` atual, não um conjunto de correções pontuais.

---

## 2. Arquitetura Macro

```
┌─────────────────────────────────────────────────────────────┐
│                        WhatsApp                              │
└─────────────────────┬───────────────────────────────────────┘
                      │ mensagem do usuário
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Webhook (FastAPI)                         │
│   POST /webhook · valida autenticidade · dedup por          │
│   message_id · enfileira (fila por usuario_id) · 200 OK     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Worker (consumer da fila)                       │
│   micro-debounce ~5s (agrupa fragmentos com "\n")           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Classificador (LLM #1)                      │
│   mensagem + histórico + estado_pendente → Intencao tipada  │
└──────┬──────────────────────────────────────────────────────┘
       │
       ├── cadastrar ───► [Extração LLM #2 c/ injection] ► Tool Cadastrar
       ├── listar ──────►                                  Tool Listar
       ├── atualizar ───► [Extração LLM #2 c/ injection] ► Tool Atualizar
       ├── excluir ─────►                                  Tool Excluir
       ├── conversar ───► Tool Conversar (LLM #2 verbaliza)
       ├── confirmar / cancelar / selecionar / complementar
       │                ► Roteador resolve via estado pendente
       └── desconhecida ► Resposta padrão (menu)
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Formatador (templates   │
                    │  Python — sem LLM)       │
                    └────────────┬────────────┘
                                 │
                                 ▼
                          WhatsApp (resposta)
```

**Chamadas LLM por mensagem:** 1 (classificador) para a maioria; +1 extração especializada para `cadastrar`/`atualizar` complexos; +1 verbalização apenas em `conversar`. Hoje o caminho comum custa 4 chamadas — a meta é ≤ 2.

---

## 3. Componentes

### 3.1 Webhook

**Responsabilidade:** receber, autenticar, deduplicar e enfileirar. **Não faz:** interpretação, lógica de negócio.

```
POST /webhook
  ├── valida autenticidade (apikey/assinatura da Evolution API)
  ├── descarta: evento ≠ messages.upsert · fromMe · sem texto
  ├── dedup por message_id (retry da Evolution não duplica)
  ├── extrai: usuario_id, mensagem, timestamp
  ├── enfileira (fila por usuario_id — garante ordem por usuário)
  └── retorna 200 OK imediatamente
```

### 3.2 Worker / Fila

- Consumer assíncrono no mesmo serviço (asyncio task) ou processo dedicado.
- **Micro-debounce** de ~5s por usuário: agrupa mensagens fragmentadas antes de processar, juntando com **`\n`** (preserva a detecção de múltiplos itens).
- Erro no processamento → o usuário **sempre recebe** uma mensagem de falha amigável (nunca silêncio).

### 3.3 Classificador

Única chamada LLM de roteamento. Especificação completa, inventário das **10 intenções**, regras de pendência e exemplos: ver [`classificador.md`](classificador.md).

**Pontos estruturais:**

- Saída via `with_structured_output` com **union discriminada** — schema Pydantic tipado por ação (`Decimal`, `date` com coerção, `Literal`). Nada de `dict` livre.
- Recebe `{historico_recente}` e `{estado_pendente}` no contexto — sem isso, "confirmar", "2" e "foi 350" são inclassificáveis.
- `confianca < 0.7` → `desconhecida`. (Nota: floats de confiança de LLM são mal calibrados; se na prática o corte oscilar, trocar por bandas `Literal["alta","media","baixa"]`.)

### 3.4 Roteador

Código Python puro, sem LLM.

```python
def rotear(intencao: Intencao, estado: EstadoConversa | None) -> Resultado:
    match intencao.acao:
        case "confirmar" | "cancelar" | "selecionar" | "complementar":
            if estado is None:                # guarda: resposta sem pendência
                return resposta_padrao()
            return resolver_pendencia(intencao, estado)
        case "cadastrar":  return tool_cadastrar(intencao.parametros)
        case "listar":     return tool_listar(intencao.parametros)
        case "atualizar":  return tool_atualizar(intencao.parametros)
        case "excluir":    return tool_excluir(intencao.parametros)
        case "conversar":  return tool_conversar(mensagem, historico)
        case _:            return resposta_padrao()
```

**Regra de ouro da pendência:** se chega intenção operacional nova com pendência ativa, a pendência é **cancelada** e a intenção nova processada (elimina o sequestro de mensagem do código atual).

### 3.5 Tools

Cada Tool é **autossuficiente e determinística**: recebe parâmetros tipados, executa regra de negócio em Python, devolve resultado estruturado. Nenhuma Tool chama outra Tool. Matemática sempre em `Decimal`.

> Os arquivos `fluxo-atendimento-*.md` deste diretório são a **especificação de comportamento** de cada Tool (regras + templates de resposta). As regras viram código Python; os templates viram template strings do Formatador — **não** são prompts de runtime.

#### Tool Cadastrar — spec: [`fluxo-atendimento-cadastro.md`](fluxo-atendimento-cadastro.md)

```
Entrada:  itens tipados (1..N) extraídos pelo classificador/extrator
Processamento (Python):
  1. Regras de inferência: forma não informada → PIX · menção a parcela/cartão → CARTÃO_CRÉDITO
  2. PIX/débito → PAGO · crédito/boleto → PENDENTE (vencimento)
  3. Parcelado: gera parcela atual + FUTURAS (anteriores não são cadastradas — §9 decisões)
     · mesmo grupo_parcela_id · valor da parcela repetido · dia preservado avançando o mês
  4. Categorização (LLM extrator ou regra) com o enum rico atual
  5. Campos obrigatórios faltantes → sinalizar na confirmação
  6. NUNCA salva direto: monta registro(s) e devolve para confirmação
Saída:    {status: "aguardando_confirmacao", registros: [...], campos_faltantes: [...]}
```

A confirmação pendente guarda o **registro já montado** (extração + categoria + parcelas calculadas) — o `confirmar` apenas persiste, **sem nova chamada LLM**.

#### Tool Listar — spec: [`fluxo-atendimento-lista.md`](fluxo-atendimento-lista.md)

```
Entrada:  periodo, categoria, responsavel, status
Processamento (Python/SQL):
  1. Filtros → query SQL (agregação no banco)
  2. Agrupar por categoria; parcelados destacados em seção própria (agrupamento VISUAL)
  3. Subtotais, total geral, split pago/pendente — tudo Decimal
Saída:    {registros, subtotais, total, pendente, pago}
```

Cobre **toda pergunta que precisa de números**: "quanto gastei?", "estou no azul?", "maior gasto". Rota 100% determinística — zero LLM na resposta.

#### Tool Atualizar — spec: [`fluxo-atendimento-atualizar.md`](fluxo-atendimento-atualizar.md)

```
Entrada:  referencia, campo, novo_valor
Processamento:
  1. RAG pela referência (3 faixas — §3.6)
  2. Múltiplos candidatos → lista numerada p/ seleção (estado guarda candidatos)
  3. Único → diff (antigo → novo) p/ confirmação
  4. campo ∈ {valor, data} com parcelas futuras vinculadas → propaga para as FUTURAS
     (valor = valor da parcela; data = mesmo dia avançando o mês) e lista as afetadas
  5. Inclui marcar pago (campo=status) — sem propagação
Saída:    {status: "aguardando_confirmacao", registro, diff, parcelas_afetadas}
```

#### Tool Excluir — spec: [`fluxo-atendimento-excluir.md`](fluxo-atendimento-excluir.md)

```
Entrada:  referencia OU filtros (periodo/categoria)
Processamento:
  modo individual (tem referência nominal):
    1. RAG (3 faixas) → ambíguo lista p/ seleção
    2. Com parcelas vinculadas → pergunta escopo como opções numeradas
       (1. somente este · 2. todos incluindo futuras)
  modo lote (só filtros):
    1. count no banco → "Encontrei N registros em {período}"
    2. confirmação explícita antes de excluir
Saída:    {status: "aguardando_confirmacao", ...}
```

#### Tool Conversar

```
Entrada:  mensagem, historico_recente
Processamento:
  1. Diálogo financeiro PURO — sem cálculo, sem consulta profunda ao banco
  2. LLM com injection própria (06-conversar.md) responde orientação/conceito/conversa
  3. Pergunta que exige números → é papel do `listar` (fronteira no classificador)
Saída:    {resposta: "texto livre"}
```

### 3.6 RAG (busca de registros)

Usado por **Atualizar** e **Excluir** para resolver referência nominal.

- **Indexação:** embedding de `descricao + categoria + tipo + data` por registro, filtrado por `usuario_id`.
- **Query:** embeda apenas a **referência extraída** pelo classificador ("flores", "zara") — nunca a mensagem crua com verbos de comando.
- **Três faixas de decisão** (calibrar limiares com dados reais):

```
match confiante (1 candidato claramente acima)  → prosseguir direto
zona ambígua (2+ candidatos próximos)            → listar opções numeradas
abaixo do piso                                   → "não encontrei, pode detalhar?"
```

### 3.7 Formatador

**Templates Python puros** — sem LLM. Recebe `{acao, status, dados}` e aplica o template WhatsApp correspondente (definidos nos `fluxo-atendimento-*.md`). Nunca toma decisão de negócio, nunca recalcula valor.

Única exceção: `conversar`, cuja resposta já vem em linguagem natural da própria Tool.

### 3.8 Gerenciador de Estado

Atrás de uma interface (`EstadoStore`), com implementação Redis **ou** Postgres (decisão no plano técnico — §7).

```python
class EstadoConversa(BaseModel):
    usuario_id: int
    acao_pendente: Literal["cadastrar", "atualizar", "excluir"] | None
    payload_pendente: dict | None       # registro(s) JÁ MONTADO(S) aguardando confirmação
    campos_faltantes: list[str]         # p/ complementar ("valor", "parcelas")
    opcoes: list[OpcaoPendente] | None  # candidatos numerados p/ selecionar
    historico: list[Mensagem]           # últimas N mensagens
    expira_em: datetime                 # TTL 5 min p/ pendência
```

- TTL da **pendência**: 5 minutos. TTL do **histórico**: mais longo (ex. 24h), são coisas distintas.
- `selecionar`/`complementar`/`confirmar`/`cancelar` só fazem sentido com estado — guarda no roteador.

### 3.9 Sistema de prompts (injection)

Estrutura definida em [`readme.md`](readme.md) e [`prompt-base.md`](prompt-base.md): um `00-base.md` com identidade + variáveis de contexto, e um placeholder `{injection_acao}` que recebe **apenas** o prompt da chamada em questão — sem contaminação de regras entre ações.

```
prompts/
├── 00-base.md            # identidade + contexto (todas as chamadas LLM)
├── 01-classificador.md   # ver classificador.md deste diretório
├── 02-extracao-cadastrar.md
├── 03-extracao-atualizar.md
└── 06-conversar.md
```

**Ajustes sobre a versão original do injection:**

1. Só existem prompts para chamadas LLM **reais**: classificador, extrações especializadas e conversar. Listar/Excluir não têm chamada LLM própria (parâmetros simples saem do classificador) — não têm injection.
2. Nova variável obrigatória: **`{estado_pendente}`** (resumo da pendência ativa).
3. `{responsavel_padrao}` vem de configuração do usuário — nunca hardcoded.
4. Categorias do `00-base.md` = **enum rico atual** (ver §5).

---

## 4. Fluxo Completo por Caso de Uso

### 4.1 Cadastro simples (PIX)

```
Usuário: "Gastei 472 reais com Claude code"
  → Classificador: {acao: cadastrar, itens: [{descricao: "Claude Code", valor: 472}]}
  → Tool Cadastrar (Python): PIX · PAGO · hoje · categoria → monta registro
  → Estado: payload_pendente = registro montado
  → Formatador: card de confirmação (template)
Usuário: "confirmar"
  → Classificador (com estado_pendente): {acao: confirmar}
  → Roteador: persiste payload_pendente — SEM nova chamada LLM
  → Formatador: "✅ Registrado com sucesso!"
```

### 4.2 Cadastro parcelado com campo faltante

```
Usuário: "Comprei roupas na zara mês passado, 3/5 vence dia 10 de julho"
  → Classificador: {acao: cadastrar, itens: [{descricao: "Roupas Zara",
      parcela_atual: 3, total_parcelas: 5, dia_vencimento: 10, ...}]}
  → Tool Cadastrar: CARTÃO_CRÉDITO · monta parcelas 3/5 (10/07, PENDENTE),
      4/5 (10/08), 5/5 (10/09) · valor ausente → campos_faltantes = ["valor"]
  → Formatador: card de confirmação com valor em destaque como pendente
Usuário: "180 a parcela"
  → Classificador (estado: aguardando valor): {acao: complementar, campo: valor, valor: 180}
  → Tool Cadastrar: completa o payload pendente (Python, sem re-extração)
  → Formatador: card de confirmação completo
Usuário: "confirmar"
  → Persiste 3 registros (parcela atual + 2 futuras, mesmo grupo_parcela_id)
```

### 4.3 Atualizar com ambiguidade

```
Usuário: "atualiza o gasto do cartão de junho"
  → Classificador: {acao: atualizar, referencia: "cartão junho"}
  → Tool Atualizar: RAG → 2 candidatos na zona ambígua
  → Estado: opcoes = [1. Zara, 2. Batman] · Formatador: lista numerada
Usuário: "2"
  → Classificador (estado: lista de 2 opções): {acao: selecionar, opcao: 2}
  → Tool Atualizar: segue com Batman → aguarda campo/valor (complementar)
```

### 4.4 Pergunta com números → listar (rota determinística)

```
Usuário: "Estou no azul ou no vermelho esse mês?"
  → Classificador: {acao: listar, periodo: mes_atual}
  → Tool Listar: SQL agrega receitas/gastos (Decimal)
  → Formatador (template): "📊 Jun/2026 · Receitas R$ 8.500 · Gastos R$ 1.302 · Saldo R$ 7.198 ✅"
  (zero LLM na resposta)
```

### 4.5 Conversa pura

```
Usuário: "vale a pena parcelar uma compra grande?"
  → Classificador: {acao: conversar}
  → Tool Conversar: LLM (injection conversar) responde orientação — sem tocar o banco
```

### 4.6 Intenção nova durante pendência

```
Estado: exclusão aguardando confirmação
Usuário: "gastei 30 no uber"
  → Classificador: {acao: cadastrar, ...}   ← intenção nova vence pendência
  → Roteador: cancela a exclusão pendente · processa o cadastro
  (no código atual isso viraria um "sim" forçado — bug crítico eliminado)
```

### 4.7 Intenção desconhecida

```
Usuário: "me conta uma piada"
  → Classificador: {acao: desconhecida, confianca: 0.95}
  → Resposta padrão (menu de capacidades) — template, sem LLM
```

---

## 5. Modelo de Dados

Reusa o modelo existente em `backend/models/` — **sem reescrita do data layer**.

```python
class Registro(BaseModel):              # ≈ Transacao atual
    id: int
    usuario_id: int                     # FK existente (multiusuário já implementado)
    descricao: str | None
    valor: Decimal
    data: date
    categoria: CategoriaEnum            # enum RICO atual (abaixo)
    forma_pagamento: FormaPagamentoEnum
    responsavel: str                    # default vem de config do usuário — nunca hardcoded
    status: StatusEnum
    parcela_numero: int
    parcela_total: int
    grupo_parcela_id: UUID | None
    detalhes: str | None                # ex: bandeira do cartão ("VISA")
    embedding: vector(1536)
    created_at: datetime
    updated_at: datetime

# Enums atuais mantidos:
CategoriaEnum:      ALIMENTACAO · TRANSPORTE · LAZER · EDUCACAO · GASTOS_FIXOS
                    · COMPRAS · GASTOS_PONTUAIS · INVESTIMENTO · RECEITA
FormaPagamentoEnum: PIX · CARTAO_CREDITO · CARTAO_DEBITO · BOLETO (+ DINHEIRO, nova)
StatusEnum:         PAGO · PENDENTE
```

> "PARCELAMENTOS" **não é categoria** — é agrupamento visual da Tool Listar
> (registros com `parcela_total > 1`), derivado de `grupo_parcela_id`.

---

## 6. Estrutura de Pastas

Refatoração **dentro de `agent/`**, reusando `backend/models` e `backend/repositories`:

```
agent/
├── config.py                  # pydantic-settings (modelos LLM, limiares, responsavel etc.)
├── entrypoint/
│   ├── main.py                # FastAPI + wiring (lifespan)
│   ├── webhook.py             # auth + dedup + enfileira
│   └── worker.py              # consumer da fila + micro-debounce
├── services/
│   ├── classificador.py       # LLM → Intencao (union tipada)
│   ├── roteador.py            # match acao → Tool (+ guarda de pendência)
│   ├── formatador.py          # templates Python → string WhatsApp
│   ├── estado_store.py        # interface + impl Redis/Postgres
│   └── rag.py                 # busca 3 faixas (compartilhada por atualizar/excluir)
├── tools/
│   ├── cadastrar.py
│   ├── listar.py
│   ├── atualizar.py
│   ├── excluir.py
│   └── conversar.py
├── domain/
│   ├── intencao.py            # Intencao + ParametrosPorAcao (union)
│   └── estado.py              # EstadoConversa, OpcaoPendente
├── integrations/
│   └── evolution_client.py    # + raise_for_status, retry
└── prompts/                   # 00-base, 01-classificador, extrações, conversar

backend/                       # INTOCADO — data layer + REST do dashboard
frontend/                      # INTOCADO — dashboard Flask
```

---

## 7. Decisões de Design

| Decisão | Escolha | Justificativa |
|---|---|---|
| LLM no roteador? | Não | Roteamento determinístico após classificação |
| Confirmação | **Tudo** que escreve no banco passa por confirmação | Decisão do produto; mitigação: card curto + confirmar persiste payload pronto (sem 2ª chamada LLM) |
| Categorias | Enum rico atual | Preserva dashboard, relatórios e dados; PARCELAMENTOS é só agrupamento visual |
| Lote (cadastro/exclusão) | Absorvido em `cadastrar`/`excluir` via parâmetros | Menos intenções; Tool decide o modo |
| Marcar pago | Caso de `atualizar` (campo=status) | Sem intenção dedicada |
| Estado de confirmação | Interface `EstadoStore`; Redis ou Postgres decidido no plano | Postgres evita peça nova de infra; Redis é mais simples p/ TTL — avaliar no /planejar |
| Tools | Independentes e determinísticas; nenhuma chama outra | Testável, sem acoplamento |
| Formatador com LLM? | **Não** — templates Python; LLM só em `conversar` | Elimina gpt-4o por resposta; números nunca passam por LLM |
| Parcelas | Geradas na Tool Cadastrar (Python) | Regra encapsulada |
| Parcelas anteriores (cadastro 3/5) | **Não cadastradas** — só atual + futuras | Decisão do produto; trade-off: totais retroativos não veem parcelas 1–2 |
| Prompts | Injection por ação (base + específico) | Contexto mínimo, sem contaminação entre ações |
| Datas | Relógio injetável com timezone do usuário (America/Sao_Paulo) | Servidor UTC registrava dia errado à noite |
| Observabilidade | Log de tokens/latência por chamada LLM | Custo e diagnóstico |

---

## 8. Pontos de Extensão

- **Novos canais** (Telegram, SMS): novo controller + client; o resto não muda
- **Novas Tools** (projeção, metas, extrato PDF): mesmo contrato entrada/saída
- **Múltiplos usuários**: `usuario_id` já presente em queries, estado e RAG
- **Notificações proativas** (parcela vencendo): worker separado consulta DB e publica — não interfere no fluxo
- **Conversar com dados**: futura evolução pode dar à Tool Conversar acesso a agregados read-only — hoje fora de escopo por decisão (conversar = sem cálculo)

---

## 9. Mudanças de comportamento conscientes (vs. código atual)

| O quê | Hoje | Novo | Risco aceito |
|---|---|---|---|
| Confirmação de cadastro | Salva direto | Sempre confirma | +1 mensagem por lançamento |
| Parcelas anteriores | Grupo inteiro 1..N (passadas PAGO) | Só atual + futuras | Totais retroativos incompletos p/ compras antigas |
| Pendência × mensagem nova | Mensagem vira "sim/não" forçado | Intenção nova cancela pendência | — (correção de bug) |
| Formatação de resposta | gpt-4o em toda resposta | Template Python | Respostas menos "criativas" (desejado) |
| Atualizar valor/data de parcelado | Altera só o registro | Propaga p/ parcelas futuras | Comportamento novo — coberto por confirmação com lista de afetadas |
| MARCAR_PAGO | Intenção própria | `atualizar` campo=status | Depende da qualidade do classificador |

---

## 10. Documentos relacionados

| Arquivo | Papel |
|---|---|
| [`levantamento.md`](levantamento.md) | Diagnóstico do código atual (motivação da refatoração) |
| [`classificador.md`](classificador.md) | Spec do classificador: 10 intenções, regras, exemplos, mapeamento |
| [`readme.md`](readme.md) + [`prompt-base.md`](prompt-base.md) | Sistema de injection de prompts |
| `fluxo-atendimento-cadastro.md` | Spec de comportamento da Tool Cadastrar (regras → Python, templates → Formatador) |
| `fluxo-atendimento-lista.md` | Spec da Tool Listar |
| `fluxo-atendimento-atualizar.md` | Spec da Tool Atualizar |
| `fluxo-atendimento-excluir.md` | Spec da Tool Excluir |
