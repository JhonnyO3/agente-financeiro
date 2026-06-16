# Tarefa 04 — Template loader + diretório de templates

**Stack:** python
**Depende de:** `template-loader.md` (congelado)
**Contrato:** `contracts/template-loader.md`

## Objetivo

Criar o carregador/renderizador Jinja2 (`agent/services/template_loader.py`) e os arquivos de template
em `agent/templates/`, um por ação/estado, reproduzindo o layout atual do `Formatador`.

## Arquivos (posse exclusiva)

- `agent/services/template_loader.py`
- `agent/templates/*.md` (catálogo completo do contrato)
- `tests/test_template_loader.py`

## Escopo

1. `carregar_template(nome: str) -> str` e `renderizar(nome: str, contexto: dict) -> str`.
2. `Environment(FileSystemLoader(<agent/templates>), trim_blocks=True, lstrip_blocks=True,
   keep_trailing_newline=False, autoescape=False)`, construído uma vez no módulo.
3. Criar todos os templates do catálogo (`listar_concluido.md`, `listar_vazio.md`,
   `cadastrar_confirmacao.md`, `cadastrar_concluido.md`, `atualizar_confirmacao.md`,
   `atualizar_concluido.md`, `atualizar_nao_encontrado.md`, `excluir_confirmacao.md`,
   `excluir_escopo.md`, `excluir_concluido.md`, `excluir_nao_encontrado.md`, `selecao_opcoes.md`,
   `menu.md`, `erro.md`), assumindo o protocolo `_fmt` (valores já formatados no contexto).
4. Os templates usam apenas interpolação (`{{ }}`), `{% for %}` e `{% if %}` — sem formatar números.

## Critérios de aceite → teste

- [ ] `carregar_template("menu.md")` retorna o conteúdo bruto (string não vazia)
- [ ] `renderizar("listar_vazio.md", {"periodo": "Jun/2026"})` interpola o período
- [ ] `renderizar` com lista (`grupos`/`itens`) itera corretamente via `{% for %}`
- [ ] `renderizar` com flag booleana respeita `{% if %}` (ex: bloco pendente só quando verdadeiro)
- [ ] `TemplateNotFound` ao pedir template inexistente (não engole o erro)
- [ ] Output não tem espaços/linhas extras introduzidos por blocos Jinja (config do Environment)
- [ ] Testes sem rede/DB/LLM, contexto mock

## Verificação local

```bash
uv run pytest tests/test_template_loader.py -v
```
