# Agente Financeiro via WhatsApp

Agente de IA pessoal acessível via WhatsApp para registrar, alterar, excluir e consultar gastos e investimentos. Todos os cálculos financeiros são feitos em Python — nunca pelo LLM.

## Funcionalidades

- **Cadastrar** gastos e investimentos em linguagem natural
- **Parcelamento** — cria N registros vinculados por `grupo_parcela_id`; pergunta automaticamente quando "cartão" é mencionado sem número de parcelas
- **Alterar e excluir** via busca semântica (pgvector) com confirmação explícita
- **Consultar** resumos mensais, semanais, gerais e status de parcelas por grupo
- Mensagens de outros números são descartadas silenciosamente

## Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12+ · `uv` |
| API | FastAPI · Evolution API (webhook) |
| IA | LangChain · `gpt-4o-mini` (classificação) · `gpt-4o` (resposta) · `text-embedding-3-small` |
| Banco | PostgreSQL + pgvector |
| Migrações | Alembic |

## Configuração

Crie um arquivo `.env` na raiz:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agente_financeiro
OPENAI_API_KEY=sk-...
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_INSTANCE=minha-instancia
EVOLUTION_API_KEY=sua-chave
WHATSAPP_ALLOWED_NUMBER=5511912345678
```

## Instalação e execução

```bash
# Instalar dependências
uv sync

# Subir o banco
docker compose up -d

# Aplicar migrations
uv run alembic upgrade head

# Iniciar o servidor
uv run uvicorn app.entrypoint.main:app --reload
```

Configure o webhook da Evolution API apontando para `POST /webhook/mensagem`.

## Testes

```bash
uv run pytest tests/ -v

# Teste único
uv run pytest tests/test_pipeline.py::test_sem_estado_classificador_chamado -v
```

## Arquitetura

```
WhatsApp → Evolution API webhook
    → FastAPI (filtro por número autorizado)
    → debounce 10s (acumula mensagens por número)
    → Pipeline (máquina de estados + classificador de intenção)
    → Services: Cadastrar / Alterar / Excluir / Consultar
    → TransacaoRepository (SQLAlchemy 2.0 async + pgvector)
    → PostgreSQL
    → Formatador (gpt-4o formata a resposta)
    → Evolution API (envia resposta ao WhatsApp)
```

Os prompts ficam em `prompts/` — um arquivo por responsabilidade — para facilitar refinamento independente do código.

## Exemplos de uso

```
Usuário: gastei 45 reais no mercado hoje
Agente:  ✅ Registrado!
         📅 09/06/2026  💰 R$ 45,00  🏷️ ALIMENTACAO

Usuário: comprei celular samsung 6x de 150
Agente:  ✅ Registrado em 6x!
         💰 6x de R$ 150,00 (total R$ 900,00)
         📅 Parcelas: jun/26 · jul/26 · ago/26 · set/26 · out/26 · nov/26

Usuário: resumo de junho
Agente:  📊 Junho/2026 — Total gastos: R$ 945,00
         ALIMENTACAO: R$ 45,00  |  COMPRAS: R$ 900,00

Usuário: parcelas do celular
Agente:  Celular Samsung — 6x de R$ 150,00
         1/6 jun/26 ✅ Paga
         2/6 jul/26 🔜 Próxima
         3/6 ago/26 ⏳ Futura  ...
```
