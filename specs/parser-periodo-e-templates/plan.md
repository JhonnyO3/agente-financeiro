# Plano Técnico — parser-periodo-e-templates

**Status:** Aprovado
**Spec:** `specs/parser-periodo-e-templates/spec.md` (aprovada conceitualmente)
**Contratos:** `parser-periodo.md`, `template-loader.md` (ambos **Congelados**)

> Gate humano: aprovado por jhonatas em 2026-06-15. Liberado para `/squad`.

## Arquitetura-alvo

Duas features **independentes** dentro de `agent/`, sem arquivos compartilhados entre elas:

```
Feature 1 — Período natural
  agent/services/parser_periodo.py   (novo)  parsear_periodo(periodo, relogio) -> (inicio, fim, label)
  agent/tools/listar.py              (edita) remove _resolver_periodo; chama parsear_periodo
  agent/prompts/01-classificador.md  (edita) documenta vocabulário completo de período

Feature 2 — Templates externos
  agent/services/template_loader.py  (novo)  carregar_template / renderizar (Jinja2)
  agent/templates/*.md               (novo)  um arquivo por ação/estado
  agent/services/formatador.py       (edita) monta contexto em Python + renderiza (sem strings hardcoded)
```

Fluxo F1: `Classificador → ParamsListar.periodo → ToolListar → parsear_periodo → (inicio, fim, label)`.
Fluxo F2: `ResultadoTool → Formatador (monta contexto, _fmt em Python) → template_loader.renderizar → texto`.

## Decisões

- **Jinja2 já disponível** (`jinja2 3.1.6` no `uv.lock`, transitivo do LangChain). Sem mudança em
  `pyproject.toml`. Não há risco de dependência nova; `str.format`/`string.Template` ficam como
  alternativa de contingência apenas se a equivalência de output não fechar (improvável).
- **Equivalência de output é o critério de F2:** os templates reproduzem byte a byte o texto atual;
  os testes existentes de `test_formatador.py` continuam verdes. `Environment` com
  `trim_blocks/lstrip_blocks/keep_trailing_newline=False` (ver contrato).
- **`conversar/concluido` não vira template** — é passthrough de `dados["resposta"]`, fica em Python.
- **Semana ISO** (segunda = início) no parser; cobre o caso "hoje é domingo".
- **Fallback do parser nunca lança** — qualquer entrada inválida resolve para `mes_atual`.
- **Anti-colisão:** F1 e F2 não tocam o mesmo arquivo; dentro de cada feature, a edição do consumidor
  (`listar.py` / `formatador.py`) depende do contrato congelado, não da implementação da peça nova,
  então cada tarefa toca só os arquivos que declara possuir.

## Tarefas (DAG)

| ID | Tarefa | Stack | Depende de | Arquivos (posse exclusiva) |
|----|--------|-------|-----------|----------------------------|
| 01 | Parser de período (`parsear_periodo`) — módulo puro + testes | python | `parser-periodo.md` | `agent/services/parser_periodo.py`, `tests/test_parser_periodo.py` |
| 02 | Wiring em `ToolListar`: remove `_resolver_periodo`, usa `parsear_periodo` | python | 01 | `agent/tools/listar.py` |
| 03 | Prompt do classificador: vocabulário completo de período + exemplos | python | `parser-periodo.md` | `agent/prompts/01-classificador.md` |
| 04 | Template loader (`carregar_template`/`renderizar`) + diretório `templates/` + testes | python | `template-loader.md` | `agent/services/template_loader.py`, `agent/templates/*.md`, `tests/test_template_loader.py` |
| 05 | Refatorar `Formatador` para usar templates (sem strings hardcoded) | python | 04 | `agent/services/formatador.py` |

DAG resumido:

```
parser-periodo.md  → 01 → 02
                   → 03            (paralelo a 01/02; só depende do contrato)
template-loader.md → 04 → 05
```

- **01, 03, 04** podem rodar em paralelo (nenhum compartilha arquivo).
- **02** depende de 01 (consome a função real). **05** depende de 04 (consome o loader + templates).
- F1 (`01,02,03`) e F2 (`04,05`) são independentes entre si.

## Ordem de integração

1. Contratos congelados (já neste plano).
2. **01** (parser) e **04** (loader + templates) — merge em qualquer ordem (arquivos distintos).
3. **02** (wiring de `listar.py`) após 01; **03** (prompt) a qualquer momento.
4. **05** (Formatador) após 04.
5. Verificação total: `uv run pytest tests/ -v`.

## Riscos

- **Equivalência de output (F2):** maior risco. `\n` finais, linhas em branco entre grupos de `listar`
  e espaços de blocos Jinja. Mitigação: `trim_blocks/lstrip_blocks/keep_trailing_newline=False` e
  preparar as linhas mais sensíveis (subtotais, cards) já montadas no contexto se necessário. Critério
  objetivo: `tests/test_formatador.py` verde sem alterar os testes.
- **Semana ISO no domingo:** cobrir explicitamente `hoje = domingo` em `semana_atual`/`semana_passada`.
- **`YYYY-MM-DD` vs `YYYY-MM` vs nome de mês:** ordem de desambiguação no parser (data exata → mês →
  nome → fallback).
- **Prompt como `str.format` (`prompts.py`):** não introduzir `{`/`}` literais em `01-classificador.md`.
- **Integração ponta a ponta de F1** ("quanto gastei hoje" só mostra o dia) depende do LLM classificar
  `periodo="hoje"` — verificado manualmente; os testes cobrem só o parser determinístico.

## Verificação da feature

- `uv run pytest tests/test_parser_periodo.py -v` (todos os valores do vocabulário).
- `uv run pytest tests/test_template_loader.py -v` (carregamento + renderização com contexto mock).
- `uv run pytest tests/test_formatador.py -v` (output equivalente — testes existentes verdes).
- `uv run pytest tests/test_tool_listar.py -v` (wiring de `ToolListar` intacto).
- `uv run pytest tests/ -v` verde no total.
- Manual: enviar "quanto eu gastei hoje" → resposta mostra apenas registros do dia corrente.
- `grep "semana_atual" agent/prompts/01-classificador.md` → presente.
