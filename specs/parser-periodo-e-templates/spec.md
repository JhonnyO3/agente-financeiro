# Spec: Parser de Período Natural + Templates de Resposta Externos

**Status:** Rascunho
**Feature:** `parser-periodo-e-templates`

## Contexto

Dois problemas independentes mas relacionados foram identificados na interação do agente:

1. **Período mal interpretado:** Ao receber "Quanto eu gastei hoje", o agente responde com dados do mês inteiro. A causa é dupla: o prompt do classificador não documenta "hoje" como valor válido para `periodo`; e `_resolver_periodo` em `listar.py` faz fallback silencioso para `mes_atual` para qualquer valor que não reconhece — incluindo "hoje" e "mes_passado" (que está documentado no prompt mas sem handler).

2. **Templates embutidos no código:** `agent/services/formatador.py` concentra toda a lógica de formatação como strings Python concatenadas dentro de métodos privados. Alterar o layout de qualquer resposta exige tocar em código Python, misturando apresentação com lógica.

---

## Fora de Escopo

- Multi-idioma (apenas português)
- Expressões de período relativas avançadas ("nos últimos 45 dias", "entre 01/04 e 15/05")
- Templates com condicionais complexas no arquivo externo (lógica permanece em Python)
- Internacionalização de datas
- Cache ou pré-compilação de templates
- Mudança no modelo de dados ou repositório

---

## Feature 1 — Parser de Período Natural

### Problema técnico

Caminho atual para "Quanto eu gastei hoje":

```
Mensagem → Classificador (LLM)
              ↓ periodo="mes_atual"  ← LLM não conhece "hoje" como opção
         _resolver_periodo("mes_atual")
              ↓
         range: 01/06/2026 → 30/06/2026   ← retorna o mês inteiro ❌
```

Dois pontos de falha:
- `01-classificador.md` linha 72: `periodo → "mes_atual", "mes_passado", "YYYY-MM", ou nome do mês` — sem "hoje", "ontem", datas exatas
- `agent/tools/listar.py` `_resolver_periodo`: "mes_passado" não tem handler (cai no fallback)

### Solução

Criar `agent/services/parser_periodo.py` como módulo independente e testável. O prompt `01-classificador.md` passa a documentar o vocabulário completo de períodos que o parser entende.

### Vocabulário de períodos suportados

| Valor recebido do LLM | Início | Fim | Label |
|---|---|---|---|
| `"hoje"` | hoje | hoje | `"hoje"` |
| `"ontem"` | ontem | ontem | `"ontem"` |
| `"semana_atual"` | segunda-feira desta semana | domingo desta semana | `"semana atual"` |
| `"semana_passada"` | segunda-feira da semana anterior | domingo da semana anterior | `"semana passada"` |
| `"mes_atual"` ou `None` | 1º do mês atual | último dia do mês atual | `"Jun/2026"` |
| `"mes_passado"` | 1º do mês anterior | último dia do mês anterior | `"Mai/2026"` |
| `"YYYY-MM"` (ex: `"2026-05"`) | 1º do mês | último dia do mês | `"Mai/2026"` |
| `"YYYY-MM-DD"` (ex: `"2026-06-10"`) | data exata | data exata | `"10/06/2026"` |
| nome de mês PT (ex: `"junho"`) | 1º do mês no ano atual | último dia do mês | `"Jun/2026"` |
| qualquer outro valor | 1º do mês atual | último dia do mês atual | `"Jun/2026"` (fallback) |

> Regra para semana: semana começa na segunda-feira (ISO 8601). Se hoje for domingo, "semana atual" = seg a dom desta semana ainda em andamento.

### Contrato do módulo

```python
# agent/services/parser_periodo.py

from datetime import date
from agent.services.relogio import Relogio

def parsear_periodo(periodo: str | None, relogio: Relogio) -> tuple[date, date, str]:
    """
    Resolve a string de período para (inicio, fim, label).
    Nunca levanta exceção — fallback silencioso para mes_atual.
    """
    ...
```

`_resolver_periodo` em `agent/tools/listar.py` é removido e substituído por chamada a `parsear_periodo`.

### Atualização do prompt do classificador

`agent/prompts/01-classificador.md` — seção "Regras de extração", linha de `periodo`:

```
- periodo → use EXATAMENTE um destes valores:
    "hoje"           — quando o usuário diz "hoje", "agora"
    "ontem"          — quando o usuário diz "ontem"
    "semana_atual"   — quando o usuário diz "essa semana", "esta semana"
    "semana_passada" — quando o usuário diz "semana passada"
    "mes_atual"      — quando o usuário diz "esse mês", "este mês" (padrão quando sem período)
    "mes_passado"    — quando o usuário diz "mês passado", "último mês"
    "YYYY-MM"        — para um mês específico (ex: "2026-05" para maio de 2026)
    "YYYY-MM-DD"     — para uma data específica (ex: "2026-06-10" para 10 de junho)
    "junho"          — nome do mês em português (usa ano atual)
```

Adicionar exemplos na tabela de exemplos:

| Mensagem | Saída esperada |
|---|---|
| `"quanto eu gastei hoje?"` | `acao=listar, periodo="hoje"` |
| `"o que gastei ontem?"` | `acao=listar, periodo="ontem"` |
| `"gastos dessa semana"` | `acao=listar, periodo="semana_atual"` |
| `"resumo da semana passada"` | `acao=listar, periodo="semana_passada"` |
| `"quanto gastei no dia 10?"` | `acao=listar, periodo="2026-06-10"` |
| `"gastos de maio"` | `acao=listar, periodo="2026-05"` |

### Critérios de aceitação — Feature 1

- [ ] `parsear_periodo("hoje", relogio)` retorna `(hoje, hoje, "hoje")`
- [ ] `parsear_periodo("ontem", relogio)` retorna `(ontem, ontem, "ontem")`
- [ ] `parsear_periodo("semana_atual", relogio)` retorna segunda e domingo da semana corrente
- [ ] `parsear_periodo("semana_passada", relogio)` retorna segunda e domingo da semana anterior
- [ ] `parsear_periodo("mes_passado", relogio)` retorna 1º e último dia do mês anterior (sem fallback)
- [ ] `parsear_periodo("2026-06-15", relogio)` retorna `(date(2026,6,15), date(2026,6,15), "15/06/2026")`
- [ ] `parsear_periodo("2026-06", relogio)` retorna `(date(2026,6,1), date(2026,6,30), "Jun/2026")`
- [ ] `parsear_periodo("junho", relogio)` retorna 1º e 30/06 do ano corrente
- [ ] `parsear_periodo(None, relogio)` e `parsear_periodo("mes_atual", relogio)` retornam mês atual
- [ ] `parsear_periodo("valor_invalido", relogio)` faz fallback para mês atual sem exceção
- [ ] `ToolListar` usa `parsear_periodo` — sem duplicação de lógica
- [ ] `_resolver_periodo` em `listar.py` é removido
- [ ] Testes unitários cobrem todos os valores da tabela acima (pytest, sem rede, `Relogio` mockado)
- [ ] Ao enviar "Quanto eu gastei hoje" ao agente, a resposta mostra apenas os registros do dia corrente

---

## Feature 2 — Templates de Resposta Externos

### Problema técnico

`agent/services/formatador.py` mistura lógica de formatação com apresentação:
- Strings de resposta hardcoded em Python (`_listar_concluido`, `_cadastrar_concluido`, etc.)
- Alterar qualquer texto de resposta exige editar Python e re-deployar
- Nenhuma separação entre "o que renderizar" (Python) e "como parece" (template)

### Solução

Criar `agent/templates/` com um arquivo `.md` por ação/estado. O `Formatador` carrega o template, prepara as variáveis em Python e renderiza com **Jinja2** (já disponível como dependência transitiva do LangChain).

Templates usam Jinja2 para:
- Interpolação simples: `{{ periodo }}`
- Iteração sobre listas: `{% for item in itens %}...{% endfor %}`
- Condicionais: `{% if pendente %}...{% endif %}`

Lógica que **permanece em Python** (não vai para o template):
- Formatação de `Decimal` para `"R$ 1.302,00"` (função `_brl`)
- Cálculo de emojis por status
- Agrupamento de transações por categoria

### Estrutura de templates

```
agent/
  templates/
    listar_concluido.md
    listar_vazio.md
    cadastrar_confirmacao.md
    cadastrar_concluido.md
    atualizar_confirmacao.md
    atualizar_concluido.md
    atualizar_nao_encontrado.md
    excluir_confirmacao.md
    excluir_escopo.md
    excluir_concluido.md
    excluir_nao_encontrado.md
    menu.md
    erro.md
```

### Contrato do carregador de templates

```python
# agent/services/template_loader.py

from jinja2 import Environment, FileSystemLoader

def carregar_template(nome: str) -> str:
    """Carrega e retorna o conteúdo bruto do template."""
    ...

def renderizar(nome: str, contexto: dict) -> str:
    """Carrega o template e renderiza com o contexto fornecido."""
    ...
```

### Exemplo: `listar_concluido.md`

```
📊 *Gastos de {{ periodo }}*

{% for grupo in grupos %}
*{{ grupo.titulo }}*
{% for item in grupo.itens %}
  • {{ item.descricao }} — {{ item.valor_fmt }} — {{ item.data_fmt }} — {{ item.emoji }} {{ item.status }}
{% endfor %}
_Subtotal: {{ grupo.subtotal_fmt }}_

{% endfor %}
💳 *Total do período: {{ total_fmt }}*
{% if pendente_positivo %}
⏳ *Pendente: {{ pendente_fmt }}*
{% endif %}
✅ *Pago: {{ pago_fmt }}*
```

> O sufixo `_fmt` indica que o valor já chegou formatado do Python (ex: `"R$ 1.302,00"`). O template não executa formatação numérica.

### Mapeamento: Formatador prepara contexto, template renderiza

| Responsabilidade | Onde fica |
|---|---|
| `Decimal` → `"R$ X.XXX,YY"` | Python (`_brl()`) |
| `date` → `"15/06"` | Python |
| Status → emoji `✅`/`⏳` | Python |
| Agrupamento de transações | Python |
| Layout, texto, emojis estruturais | Template `.md` |

### Critérios de aceitação — Feature 2

- [ ] Todos os templates existem em `agent/templates/`
- [ ] `Formatador.formatar()` não contém strings de resposta hardcoded (apenas montagem de contexto + chamada a `renderizar`)
- [ ] Função `_brl` e cálculo de emojis permanecem em Python
- [ ] Alterar o texto de "listar_concluido.md" sem tocar Python produz o novo texto na resposta
- [ ] Testes de `Formatador` verificam o output renderizado (não snapshot do template)
- [ ] Nenhuma regressão nas respostas existentes (output deve ser equivalente ao atual)
- [ ] `template_loader.py` tem testes unitários (carregamento + renderização com contexto mock)

---

## Dependências entre as duas features

As duas features são **independentes**: podem ser implementadas e deployadas separadamente. A ordem sugerida é:

1. Feature 1 (parser de período) — corrige o bug reportado
2. Feature 2 (templates externos) — melhoria estrutural

---

## Como Verificar

| Requisito | Como testar |
|---|---|
| F1 — "hoje" resolve corretamente | `pytest tests/test_parser_periodo.py::test_hoje` |
| F1 — "semana_atual" resolve para seg–dom | `pytest tests/test_parser_periodo.py::test_semana_atual` |
| F1 — "mes_passado" não faz fallback | `pytest tests/test_parser_periodo.py::test_mes_passado` |
| F1 — prompt atualizado com vocabulário | `grep "semana_atual" agent/prompts/01-classificador.md` |
| F1 — integração ponta a ponta | Enviar "quanto gastei hoje" → resposta mostra só registros do dia |
| F2 — template externo funciona | `pytest tests/test_template_loader.py` |
| F2 — sem hardcode no Formatador | `grep -n '"📊"' agent/services/formatador.py` → 0 resultados |
| F2 — output equivalente | `pytest tests/test_formatador.py` (testes existentes continuam passando) |
