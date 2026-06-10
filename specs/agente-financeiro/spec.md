# Spec: Agente Financeiro via WhatsApp

## Contexto

Agente de IA pessoal acessível via WhatsApp que permite ao único usuário autorizado registrar, alterar, excluir e consultar seus gastos e investimentos. Os dados são persistidos em PostgreSQL e os cálculos financeiros são realizados em código Python — nunca pelo LLM.

---

## Fora de Escopo

- Multi-usuário
- Interface web ou mobile
- Relatórios em PDF/Excel
- Notificações proativas (o agente não envia mensagens sem ser acionado)
- Integração automática com bancos ou corretoras
- Autenticação/login (segurança baseada em filtro por número de telefone)

---

## Modelo de Dados

### Tabela `transacoes`

| Campo             | Tipo          | Obrigatoriedade | Descrição                                                        |
|-------------------|---------------|-----------------|------------------------------------------------------------------|
| id                | SERIAL PK     | —               | Identificador único                                              |
| tipo              | ENUM          | Obrigatório     | `GASTO` ou `INVESTIMENTO` (IA interpreta)                        |
| valor             | DECIMAL(12,2) | Obrigatório     | Valor **por parcela** em BRL                                     |
| descricao         | TEXT          | Opcional        | Formatada e enriquecida pela IA                                  |
| categoria         | ENUM          | Obrigatório     | Ver lista abaixo (IA categoriza)                                 |
| data              | DATE          | Obrigatório     | Data de vencimento da parcela (padrão = hoje para a 1ª)         |
| parcela_numero    | INTEGER       | Obrigatório     | Número desta parcela (começa em 1)                               |
| parcela_total     | INTEGER       | Obrigatório     | Total de parcelas do grupo (1 = pagamento à vista)               |
| grupo_parcela_id  | UUID          | Obrigatório     | Identificador compartilhado por todas as parcelas do mesmo gasto |
| embedding         | VECTOR(1536)  | Interno         | Gerado pela IA para busca semântica (pgvector)                   |
| criado_em         | TIMESTAMP     | —               | Timestamp de inserção                                            |

### Categorias válidas

`ALIMENTACAO` · `TRANSPORTE` · `LAZER` · `INVESTIMENTO` · `GASTOS_FIXOS` · `COMPRAS`

> Quando `tipo = INVESTIMENTO`, a categoria é automaticamente `INVESTIMENTO`.

---

## Requisitos Funcionais

### RF-01 · Cadastrar Gasto/Investimento

**Entrada:** Mensagem de texto natural do usuário (ex: "gastei 45 reais no mercado hoje")

**Processamento:**
1. IA extrai: valor, tipo, descrição, data, parcelas
2. IA categoriza com base na lista predefinida
3. Se o usuário mencionar "cartão" sem informar parcelas → agente pergunta: "É à vista ou parcelado?"
4. Python gera um `grupo_parcela_id` (UUID) para o lançamento
5. Python cria N registros independentes no DB (um por parcela), cada um com embedding gerado
6. Datas calculadas em Python: 1ª parcela = data informada ou hoje; demais = data anterior + 30 dias

**Extração de valor pelo LLM:**
- "6x de 150" → `valor = 150`, `parcela_total = 6`
- "900 em 6x" → `valor = 150` (Python divide 900 / 6), `parcela_total = 6`
- Sem menção de parcelas → `valor = informado`, `parcela_total = 1`

**Saída:** Confirmação com resumo do parcelamento

```
✅ Gasto registrado: Celular Samsung
💰 6x de R$ 150,00 (total R$ 900,00)
📅 Parcelas: jun/26 · jul/26 · ago/26 · set/26 · out/26 · nov/26
🏷️ COMPRAS
```

**Critérios de aceitação:**
- [ ] Registro(s) inserido(s) no DB em < 3s após recebimento do webhook
- [ ] Tipo inferido corretamente em ≥ 90% dos casos de teste
- [ ] Categoria inferida corretamente em ≥ 85% dos casos de teste
- [ ] Data padrão = hoje para a 1ª parcela quando não informada
- [ ] Datas das parcelas calculadas em Python (+30 dias por parcela)
- [ ] Valor por parcela calculado em Python quando o usuário informa o total
- [ ] Todos os registros do mesmo parcelamento compartilham o mesmo `grupo_parcela_id`
- [ ] Menção a "cartão" sem parcelas dispara pergunta de confirmação antes de salvar

---

### RF-02 · Alterar um Gasto/Investimento

**Entrada:** Usuário descreve o que quer alterar com dados suficientes para identificar 1 registro (ex: "altere o gasto do mercado de ontem para 60 reais")

**Processamento:**
1. Busca semântica via pgvector para encontrar o registro mais próximo
2. Agente exibe o registro encontrado e solicita confirmação
3. Aguarda **10 segundos** para acumular mensagens subsequentes (append antes de processar)
4. Usuário confirma → alteração executada em Python

**Saída:** Confirmação com os dados atualizados

**Critérios de aceitação:**
- [ ] Busca semântica retorna o registro correto em ≥ 85% dos cenários de teste
- [ ] Agente exibe exatamente 1 candidato para confirmação (não uma lista)
- [ ] Janela de 10s para acumular input funciona corretamente
- [ ] Alteração reflete no DB imediatamente após confirmação
- [ ] Operação cancelada se usuário não confirmar dentro do fluxo

---

### RF-03 · Excluir um Gasto/Investimento

**Entrada:** Usuário descreve o registro a excluir (ex: "exclua o gasto do uber de sexta")

**Processamento:**
1. Busca semântica via pgvector
2. Agente exibe o registro encontrado e solicita confirmação explícita
3. Aguarda **10 segundos** para acumular mensagens
4. Usuário confirma → exclusão executada (hard delete)

**Saída:** Confirmação de exclusão

**Critérios de aceitação:**
- [ ] Nenhuma exclusão ocorre sem confirmação explícita do usuário
- [ ] Registro removido do DB após confirmação
- [ ] Embedding também removido junto ao registro

---

### RF-04 · Consultar / Resumos Financeiros

**Entrada:** Pergunta em linguagem natural

**Modos suportados:**
| Consulta do usuário              | Resposta esperada                                                        |
|----------------------------------|--------------------------------------------------------------------------|
| "Resumo de [mês]"                | Total gasto + breakdown por categoria no mês                             |
| "Quanto gastei essa semana?"     | Total da semana atual (seg–dom)                                          |
| "Resumo geral"                   | Saldo total: soma de gastos vs investimentos                             |
| "Parcelas do celular"            | Todas as parcelas do grupo + status (paga / futura)                     |
| Filtros dinâmicos (ex: categoria, período personalizado) | Agente interpreta e executa query SQL    |

**Processamento:**
- LLM interpreta a intenção e os filtros
- Query SQL construída e executada em Python
- Cálculos matemáticos feitos em código (nunca pelo LLM)
- Para consultas de parcelamento: agrupa por `grupo_parcela_id`, mostra todas as parcelas com status
- Resultado formatado pelo LLM para resposta em texto

**Status de parcela** (calculado em Python pela data):
- `✅ Paga` — data da parcela < hoje
- `🔜 Próxima` — data da parcela = mês atual
- `⏳ Futura` — data da parcela > mês atual

**Critérios de aceitação:**
- [ ] Totais calculados em Python com precisão de 2 casas decimais
- [ ] Resposta retornada em < 5s para consultas com até 1.000 registros
- [ ] LLM não realiza soma/divisão diretamente — delega ao código
- [ ] Consulta por grupo exibe todas as N parcelas com status correto
- [ ] Resumo mensal não duplica valor total de parcelados (conta apenas a parcela do mês)

---

### RF-05 · Mensagens Fora de Escopo

**Entrada:** Qualquer mensagem não relacionada a finanças (ex: "oi, tudo bem?")

**Saída:** Resposta amigável + menu das ações disponíveis

**Critérios de aceitação:**
- [ ] Agente responde sem ignorar o usuário
- [ ] Menu de opções é exibido (cadastrar, alterar, excluir, consultar)
- [ ] Nenhum lançamento financeiro é gerado a partir dessas mensagens

---

### RF-06 · Filtro de Número Autorizado

**Comportamento:** Qualquer mensagem recebida de número diferente do configurado em `ENV` é descartada silenciosamente — sem resposta e sem log de erro.

**Critérios de aceitação:**
- [ ] Número configurado via variável de ambiente `WHATSAPP_ALLOWED_NUMBER`
- [ ] Mensagens de outros números não geram nenhuma ação
- [ ] Teste unitário cobre o filtro

---

### RF-07 · Parcelamento

**Regras gerais:**

| Situação                              | Comportamento                                                         |
|---------------------------------------|-----------------------------------------------------------------------|
| Sem menção de parcelas                | `parcela_total = 1`, fluxo normal                                    |
| Usuário menciona "cartão" sem parcelas| Agente pergunta: "É à vista ou parcelado? Se parcelado, quantas vezes?" |
| `Nx de Y reais`                       | `valor = Y`, `parcela_total = N`                                     |
| `Total em Nx`                         | `valor = total / N` (Python calcula), `parcela_total = N`            |
| Data informada para a 1ª parcela      | Demais = data_1 + 30 dias por parcela (Python)                       |
| Data não informada                    | 1ª = hoje, demais = +30 dias (Python)                                |

**Exclusão de parcelado:**
- Ao excluir uma parcela específica → exclui somente aquela
- Ao excluir "todas as parcelas do celular" → exclui todos os registros do `grupo_parcela_id`
- Agente deve perguntar explicitamente: "Deseja excluir só esta parcela ou todas as X parcelas?"

**Critérios de aceitação:**
- [ ] N registros criados no DB com o mesmo `grupo_parcela_id`
- [ ] Cada registro tem `parcela_numero` de 1 a N e `parcela_total = N`
- [ ] Datas calculadas corretamente em Python
- [ ] Divisão de valor calculada em Python com arredondamento de 2 casas decimais
- [ ] Pergunta de parcelas disparada quando "cartão" mencionado sem quantidade

---

## Fluxo de Conversação

```
Webhook recebe mensagem
        │
        ▼
Número autorizado? ──Não──▶ Descarta silenciosamente
        │ Sim
        ▼
Aguarda 10s (acumula mensagens)
        │
        ▼
Classifica intenção (prompt: intencao.md)
        │
   ┌────┴────────────────────┐
   │                         │
Financeiro               Fora de escopo
   │                         │
   ▼                         ▼
Roteador de ações      Resposta + menu (prompt: fora-de-escopo.md)
   │
   ├── Cadastrar ──▶ Extrai dados
   │                    │
   │               Menciona "cartão" sem parcelas?
   │                    ├── Sim ──▶ Pergunta parcelas → aguarda resposta
   │                    └── Não ──▶ Python gera grupo_parcela_id
   │                                Python cria N registros → Confirma
   │
   ├── Alterar   ──▶ Busca semântica → Exibe (com "Parcela X/N") → Confirma → Altera
   │
   ├── Excluir   ──▶ Busca semântica → Exibe → Pergunta: parcela única ou todas?
   │                                          → Confirma → Exclui
   │
   └── Consultar ──▶ Interpreta filtros → Query SQL → Formata (com status parcelas) → Responde
```

---

## Stack Técnica

| Componente        | Tecnologia                                         |
|-------------------|----------------------------------------------------|
| Linguagem         | Python 3.12+                                       |
| Package manager   | `uv`                                               |
| Orquestração IA   | LangChain + `langchain-openai`                     |
| Modelos LLM       | `gpt-4o-mini` (classificação) · `gpt-4o` (resposta) |
| Embeddings        | `text-embedding-3-small` (1536d) via OpenAI        |
| Banco de dados    | PostgreSQL + pgvector                              |
| WhatsApp          | Evolution API via webhook                          |
| Migrações         | Alembic                                            |
| Arquitetura       | Camadas (entrypoint → service → repository)        |

---

## Estrutura de Prompts

Os prompts são mantidos em `prompts/` como arquivos Markdown independentes para facilitar o refinamento incremental:

| Arquivo                      | Responsabilidade                                      |
|------------------------------|-------------------------------------------------------|
| `prompts/sistema.md`         | Identidade e regras globais do agente                 |
| `prompts/intencao.md`        | Classifica a intenção da mensagem recebida            |
| `prompts/categorizacao.md`   | Escolhe a categoria correta para o lançamento         |
| `prompts/confirmacao.md`     | Fluxo de exibição e confirmação (alterar/excluir)     |
| `prompts/resumo.md`          | Formata o resumo financeiro para resposta             |
| `prompts/fora-de-escopo.md`  | Resposta para mensagens não financeiras               |

---

## Como Verificar

| Requisito | Como testar                                                                                          |
|-----------|------------------------------------------------------------------------------------------------------|
| RF-01     | Enviar mensagem de gasto → checar registro no DB com campos corretos                                 |
| RF-02     | Enviar alteração com dados parciais → confirmar → checar DB atualizado                               |
| RF-03     | Enviar exclusão de parcela única → confirmar → checar remoção; demais parcelas intactas             |
| RF-04     | Pedir resumo mensal → verificar total bate com soma SQL independente                                 |
| RF-04     | Pedir "parcelas do [gasto]" → verificar todas as N parcelas com status correto                      |
| RF-05     | Enviar "oi" → verificar resposta + menu exibido, sem registro no DB                                  |
| RF-06     | Simular webhook de número não autorizado → verificar ausência de resposta                            |
| RF-07     | Enviar "comprei celular 6x de 150" → checar 6 registros com mesmo `grupo_parcela_id` no DB          |
| RF-07     | Enviar "900 em 6x" → checar `valor = 150.00` em cada registro                                       |
| RF-07     | Enviar "comprei no cartão" → checar que agente pergunta sobre parcelas antes de salvar               |
| RF-07     | Enviar "exclua todas as parcelas do celular" → checar remoção dos N registros do grupo              |
| Cálculos  | Inserir 5 lançamentos conhecidos → pedir resumo → verificar soma em Python                           |
