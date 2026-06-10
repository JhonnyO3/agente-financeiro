# Exploração — Agente Financeiro

## Estado do repositório

Projeto novo, sem código de produção. Apenas:
- `specs/negocio.md` — requisitos de negócio originais
- `specs/agente-financeiro/spec.md` — spec técnica aprovada
- `prompts/*.md` — 6 arquivos de prompt separados por responsabilidade

## Convenções a adotar (definidas na spec)

- **Linguagem:** Python 3.12+
- **Orquestração IA:** LangChain
- **Banco:** PostgreSQL + pgvector
- **Webhook:** Evolution API
- **Migrações:** Alembic
- **Arquitetura:** Camadas (`entrypoint → service → repository`)
- **Sem comentários no código**
- **Sem validações excessivas**

## Estrutura de diretórios proposta

```
agente-financeiro/
├── app/
│   ├── entrypoint/         # FastAPI — webhook receiver
│   ├── services/           # lógica de negócio por caso de uso
│   ├── repositories/       # acesso ao banco (SQLAlchemy)
│   ├── models/             # modelos ORM + enums
│   ├── agents/             # chains LangChain por intenção
│   └── config.py           # settings via pydantic-settings
├── prompts/                # já existente
├── migrations/             # Alembic
├── tests/
├── .env.example
├── docker-compose.yml
└── pyproject.toml
```

## Integrações externas

| Sistema       | Protocolo  | Direção       | Notas                                      |
|---------------|------------|---------------|--------------------------------------------|
| Evolution API | HTTP/Webhook | entrada      | POST no endpoint do agente                 |
| Evolution API | HTTP/REST  | saída         | POST para enviar mensagem de volta         |
| PostgreSQL    | TCP        | interna       | SQLAlchemy async + pgvector extension      |
| LLM (Claude)  | HTTP/REST  | interna       | via LangChain `ChatAnthropic`              |

## Riscos identificados

| Risco                              | Mitigação                                                          |
|------------------------------------|--------------------------------------------------------------------|
| LLM alucinando cálculos            | Todo math em Python; LLM só interpreta intenção e formata texto   |
| Debounce de 10s no webhook         | Implementar com `asyncio` task + cache TTL por número de telefone |
| pgvector dimension mismatch        | Fixar dimensão no migration (1536 para `text-embedding-3-small`)  |
| Exclusão acidental de parcelado    | Sempre perguntar: parcela única vs grupo inteiro                  |
| Divisão não exata em parcelas      | Arredondar com `Decimal` + absorver centavo na última parcela     |

## Reuso identificado

- `prompts/` já criado — carregar via `Path(__file__).parent / "prompts"` no config
- Nenhum código existente para reaproveitar
