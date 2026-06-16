# Exploração — parser-periodo-e-templates

## Território

Duas fronteiras independentes, ambas dentro de `agent/`:

### Feature 1 — resolução de período (`agent/tools/listar.py`)

- `_resolver_periodo(periodo: str | None, relogio: Relogio) -> tuple[date, date, str]`
  (linhas 49–80) já existe e cobre: `None`/`mes_atual`, formato `YYYY-MM` e nome de mês PT.
  **Não trata** `hoje`, `ontem`, `semana_atual`, `semana_passada`, `mes_passado`, `YYYY-MM-DD`.
- Tabelas auxiliares já presentes no módulo: `_MESES_PT` (nome→nº, com `março`/`marco`),
  `_MESES_LABEL` (nº→`Jan`..`Dez`) e o helper `_primeiro_e_ultimo_dia(ano, mes)` via `calendar.monthrange`.
  Tudo isso migra para o novo módulo `parser_periodo.py`.
- `ToolListar.executar` (linha 89) consome a tupla `(inicio, fim, periodo_label)`. O único ponto de
  troca é a linha 90: `_resolver_periodo(...)` → `parsear_periodo(...)`. Assinatura idêntica.
- `Relogio.hoje()` (`agent/services/relogio.py`) devolve `date` no fuso do usuário e aceita `_fixed`
  para testes determinísticos — é o que os testes usam para fixar "hoje".
- `ParamsListar.periodo` (`agent/domain/intencao.py`) é `str | None`, sem `Literal` — o parser recebe
  texto livre e nunca pode levantar exceção (fallback obrigatório).
- Prompt `agent/prompts/01-classificador.md`: a linha 71 (`periodo → "mes_atual", "mes_passado", ...`)
  e a tabela de exemplos (linhas 78–97) precisam do vocabulário completo. O carregamento de prompts
  (`agent/services/prompts.py`) usa `str.format()` — o `.md` do classificador **não** tem chaves `{}`
  de template hoje, então adicionar exemplos é seguro desde que não se introduza `{`/`}` literais.

### Feature 2 — templates externos (`agent/services/formatador.py`)

- `Formatador.formatar(resultado: ResultadoTool) -> str` é **síncrono** e determinístico (sem LLM,
  apesar do docstring antigo nos testes). Despacha via `match (acao, status)` para helpers `_*`.
- Strings hardcoded espalhadas em: `_listar_concluido`, `_cadastrar_confirmacao`,
  `_cadastrar_concluido`, `_atualizar_confirmacao`, `_excluir_confirmacao`, `_excluir_escopo`,
  `_excluir_concluido`, `_selecao_opcoes`, e nos blocos inline de `listar/vazio`, `atualizar/concluido`,
  `atualizar/nao_encontrado`, `excluir/nao_encontrado`, `menu/concluido`, `erro/concluido`, fallback.
- Lógica que **fica em Python** (não vai para o template): `_brl` (Decimal→`R$ 1.302,00`),
  `_status_emoji`, `_card_registro`, agrupamento por categoria, separação de parcelados, totais,
  diff inline de `_atualizar_confirmacao`, dedup por descrição em `_cadastrar_concluido`.
- A casa já adota a convenção do sufixo `_fmt`: o Python entrega valores já formatados ao template.

## Reuso

- `Jinja2 3.1.6` **já disponível** no `uv.lock` (transitivo via LangChain) — `from jinja2 import ...`
  funciona sem alterar `pyproject.toml`. Decisão: usar `jinja2`.
- `Relogio` mockável é o padrão de data dos testes (`_fixed`).
- `_MESES_PT`/`_MESES_LABEL`/`_primeiro_e_ultimo_dia` são reaproveitados pelo parser.

## Convenções reais

- `uv` para tudo; `pytest` + `pytest-asyncio` (`asyncio_mode=auto`); **sem ruff/mypy** no repo.
- Testes usam mocks, sem DB/LLM real; data fixada via `Relogio(tz, _fixed=...)`.
- Sem comentários supérfluos; código enxuto (CLAUDE.md + `rules/python.md`).
- Cada teste seta env mínimo via `os.environ.setdefault` e/ou importa o alvo dentro da função.

## Integrações / pontos de toque

- `ToolListar` é o único consumidor de `_resolver_periodo`. (`grep` confirma uso só em `listar.py`.)
- `Formatador` é consumido pela pipeline para gerar o texto final ao usuário.
- Os testes existentes `tests/test_tool_listar.py` e `tests/test_formatador.py` definem o output
  esperado atual — a Feature 2 não pode regredir esse output (equivalência byte a byte).

## Riscos / atenção

- **Equivalência de output (F2):** o texto renderizado pelos templates Jinja deve bater com o atual.
  Atenção a `\n` finais, linhas em branco entre grupos e `trim_blocks`/`lstrip_blocks` do Jinja —
  recomenda-se montar a maior parte das linhas em Python e usar o template para o esqueleto, OU
  configurar o `Environment` para não introduzir espaços/linhas extras. Critério: testes de
  `test_formatador.py` continuam verdes.
- **Semana ISO (F1):** segunda = início (`date.weekday()==0`). "semana atual" quando hoje é domingo
  ainda devolve seg–dom desta semana. Cobrir explicitamente o caso domingo.
- **`YYYY-MM-DD` vs `YYYY-MM`:** desambiguar por tamanho/estrutura antes do nome de mês.
- **Fallback nunca lança:** qualquer `ValueError` de parsing cai em `mes_atual` silenciosamente.
- **Prompt como template (`str.format`):** não introduzir `{`/`}` literais em `01-classificador.md`.
