# Plano Técnico — Agente Financeiro via WhatsApp

**Status: APROVADO**  
**Spec:** `specs/agente-financeiro/spec.md`  
**Data:** 2026-06-09

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                    WhatsApp (usuário)                    │
└───────────────────────┬─────────────────────────────────┘
                        │ webhook POST
┌───────────────────────▼─────────────────────────────────┐
│  entrypoint/webhook.py  — FastAPI                        │
│  • Filtra número autorizado (ENV)                        │
│  • Debounce 10s por número (asyncio)                     │
└───────────────────────┬─────────────────────────────────┘
                        │ texto acumulado
┌───────────────────────▼─────────────────────────────────┐
│  services/pipeline.py                                    │
│  • Verifica estado de confirmação pendente               │
│  • Classifica intenção (agents/classificador.py)         │
│  • Despacha para service correto                         │
└───┬──────────┬──────────┬──────────┬────────────────────┘
    │          │          │          │
  CADASTRAR  ALTERAR  EXCLUIR  CONSULTAR  FORA_DE_ESCOPO
    │          │          │          │          │
┌───▼──┐  ┌───▼──┐  ┌────▼──┐  ┌───▼──┐  ┌───▼──┐
│svc   │  │svc   │  │svc    │  │svc   │  │direto│
│cada  │  │alter │  │excluir│  │consul│  │prompt│
│strar │  │.py   │  │.py    │  │tar.py│  └──────┘
└──┬───┘  └──┬───┘  └───┬───┘  └──┬───┘
   │         │           │         │
   └─────────┴───────────┴─────────┘
                    │
        ┌───────────▼───────────┐
        │ repositories/         │
        │ transacao_repository  │
        │ PostgreSQL + pgvector │
        └───────────────────────┘
                    │
        ┌───────────▼───────────┐
        │ services/formatador   │
        │ LLM formata resposta  │
        └───────────────────────┘
                    │
        ┌───────────▼───────────┐
        │ integrations/         │
        │ evolution_client.py   │
        │ envia mensagem back   │
        └───────────────────────┘
```

---

## Decisões de Arquitetura

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Cálculos matemáticos | Python `Decimal` | Nunca delegar ao LLM |
| Provedor LLM | OpenAI (`gpt-4o` / `gpt-4o-mini`) | `gpt-4o-mini` para classificação (custo), `gpt-4o` para resposta |
| Package manager | `uv` | Lock file determinístico, instalação rápida |
| Embedding | `text-embedding-3-small` (1536d) via OpenAI | Custo/qualidade para português |
| Busca semântica | pgvector L2 distance | Sem infra extra (já no Postgres) |
| Estado de confirmação | Dict em memória + TTL 5min | Simples; usuário único |
| Debounce | `asyncio.call_later` | Sem dependência externa |
| Divisão de parcelas | Último absorve centavo restante | Padrão financeiro brasileiro |
| Hard delete | Sim | Sem requisito de auditoria |
| Async | SQLAlchemy async + asyncpg | Performance para I/O bound |

---

## Tabela de Tarefas e DAG

| ID | Tarefa                        | Stack  | Depende de | Paralelo com |
|----|-------------------------------|--------|------------|--------------|
| 01 | Setup do projeto              | python | —          | —            |
| 02 | Modelos DB + Alembic          | python | 01         | 04, 05       |
| 03 | TransacaoRepository           | python | 02         | 04, 05       |
| 04 | Webhook Receiver + Debounce   | python | 01         | 02, 05       |
| 05 | Agent Chains (LangChain)      | python | 01         | 02, 04       |
| 06 | Service Cadastrar             | python | 03, 05     | 07, 08       |
| 07 | Service Alterar/Excluir       | python | 03, 05     | 06, 08       |
| 08 | Service Consultar             | python | 03, 05     | 06, 07       |
| 09 | Pipeline + Formatador         | python | 06, 07, 08 | —            |
| 10 | Integração Evolution + Wiring | python | 04, 09     | —            |

### DAG visual

```
01
├── 02 → 03 ─────────────┐
├── 04 ──────────────────┤→ 09 → 10
└── 05 ──────────────────┤
         06, 07, 08 ─────┘
         (paralelo entre si)
```

---

## Contratos Congelados

| Arquivo                             | Fronteira                              |
|-------------------------------------|----------------------------------------|
| `contracts/webhook.md`              | Evolution API → entrypoint             |
| `contracts/transacao-repository.md` | services → repository → banco          |
| `contracts/agent-llm.md`           | services → LangChain chains → LLM      |
| `contracts/evolution-api.md`        | pipeline → Evolution API (envio)       |
| `contracts/embedding.md`            | services → embedder → OpenAI           |

---

## Cenários de Teste (QA)

| Arquivo                                    | Cobertura                        |
|--------------------------------------------|----------------------------------|
| `scenarios/01-cadastrar.feature`           | RF-01, RF-06                     |
| `scenarios/02-parcelamento.feature`        | RF-07                            |
| `scenarios/03-alterar-excluir.feature`     | RF-02, RF-03                     |
| `scenarios/04-consultar.feature`           | RF-04                            |
| `scenarios/05-fora-escopo-seguranca.feature` | RF-05, RF-06                   |

---

## Riscos e Mitigações

| Risco                                | Impacto | Mitigação                                          |
|--------------------------------------|---------|----------------------------------------------------|
| LLM retorna categoria errada         | Médio   | Categoria auditável no DB; usuário pode corrigir   |
| Debounce perde mensagem em crash     | Baixo   | Usuário único; reenvio é trivial                   |
| pgvector dimension mismatch          | Alto    | Fixar 1536 no migration e no chain de embedding    |
| Divisão de parcela com arredondamento| Médio   | `Decimal` + absorver centavo na última parcela      |
| Estado de confirmação em memória     | Baixo   | TTL 5min + usuário único; restart limpa estado     |

---

## Ordem de Integração

1. `01` → ambiente rodando
2. `02` + `03` → banco com dados testáveis
3. `05` → chains validadas com testes unitários
4. `06`, `07`, `08` em paralelo → services testados isoladamente
5. `04` → webhook recebendo e despachando
6. `09` → pipeline ponta a ponta sem Evolution
7. `10` → ciclo completo com WhatsApp real

---

## Como Verificar a Feature Completa

1. `docker compose up -d` → banco no ar
2. `uv run alembic upgrade head` → schema criado
3. `uv run uvicorn app.entrypoint.main:app --reload` → servidor no ar
4. Configurar webhook da Evolution API apontando para `POST /webhook/mensagem`
5. Enviar mensagens do número autorizado e verificar respostas no WhatsApp
6. Checar registros no banco com `SELECT * FROM transacoes ORDER BY criado_em DESC LIMIT 10`
