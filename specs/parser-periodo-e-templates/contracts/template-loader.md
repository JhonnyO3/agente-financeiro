# Contrato: Carregador e Renderizador de Templates

**Status:** Congelado
**Fronteira:** `agent/services/template_loader.py` (novo) + diretório `agent/templates/*.md`,
consumido por `agent/services/formatador.py`

## Assinatura

```python
# agent/services/template_loader.py
from jinja2 import Environment, FileSystemLoader

def carregar_template(nome: str) -> str:
    """Carrega e retorna o conteúdo bruto do template `agent/templates/<nome>`."""

def renderizar(nome: str, contexto: dict) -> str:
    """Carrega o template `<nome>` e renderiza com o contexto fornecido."""
```

- `nome` é o nome do arquivo com extensão (ex: `"listar_concluido.md"`).
- Diretório base: `agent/templates/`, resolvido relativo ao pacote (`Path(__file__).parents[1] / "templates"`).
- Engine: **Jinja2 3.1.6** (já no `uv.lock`).

## Configuração obrigatória do Environment (congelada)

Para garantir equivalência de output com o Formatador atual:

```python
Environment(
    loader=FileSystemLoader(<dir templates>),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=False,
    autoescape=False,           # saída é texto WhatsApp, não HTML
)
```

- `autoescape=False`: não escapar `&`, `<`, etc. (texto puro).
- `trim_blocks`/`lstrip_blocks`: tags de bloco (`{% %}`) não introduzem linhas/espaços extras.
- `keep_trailing_newline=False`: o template não força `\n` final indesejado.
- O Environment é construído uma única vez no módulo (constante), não por chamada.

## Protocolo de contexto (sufixo `_fmt`)

Toda formatação numérica/data/emoji é feita em **Python** e entregue pronta ao template. O template
só interpola e itera. Convenção de nomes no `contexto`:

| Chave | Tipo | Significado |
|---|---|---|
| `*_fmt` | `str` | valor já formatado pelo Python (ex: `valor_fmt="R$ 1.302,00"`, `data_fmt="15/06"`) |
| `emoji` | `str` | emoji de status já calculado (`✅`/`⏳`) |
| `*_positivo` ou flags booleanas | `bool` | controlam `{% if %}` (ex: `pendente_positivo`) |
| listas (`grupos`, `itens`, `registros`...) | `list[dict]` | iteradas com `{% for %}` |

O template **nunca**: formata `Decimal`, calcula emoji, agrupa transações, monta diff inline.

## Catálogo de templates (um por ação/estado)

```
agent/templates/
  listar_concluido.md          (listar, concluido)
  listar_vazio.md              (listar, vazio)
  cadastrar_confirmacao.md     (cadastrar, aguardando_confirmacao | aguardando_complemento)
  cadastrar_concluido.md       (cadastrar, concluido)
  atualizar_confirmacao.md     (atualizar, aguardando_confirmacao)
  atualizar_concluido.md       (atualizar, concluido)
  atualizar_nao_encontrado.md  (atualizar, nao_encontrado)
  excluir_confirmacao.md       (excluir, aguardando_confirmacao)
  excluir_escopo.md            (excluir, aguardando_escopo)
  excluir_concluido.md         (excluir, concluido)
  excluir_nao_encontrado.md    (excluir, nao_encontrado)
  selecao_opcoes.md            (atualizar|excluir, aguardando_selecao)
  menu.md                      (menu, concluido)
  erro.md                      (erro, concluido / fallback)
```

> `selecao_opcoes.md` cobre `aguardando_selecao` de atualizar e excluir (mesmo layout, `verbo` no contexto).
> `conversar/concluido` devolve `dados["resposta"]` cru — **não usa template** (passthrough), mantido em Python.

## Equivalência de output (requisito de aceite)

Para cada `(acao, status)`, `Formatador.formatar(resultado)` deve produzir **exatamente** o mesmo texto
de antes (os testes de `tests/test_formatador.py` continuam verdes). A montagem em Python deve preparar o
contexto de modo que o template gere esse texto sem `\n` extras nem espaços em branco no fim das linhas.

## Garantias

- `carregar_template`/`renderizar` são puros sobre `(nome, contexto)`; sem rede, sem LLM.
- Template ausente: Jinja levanta `TemplateNotFound` (erro de programação, não tratado silenciosamente).
- `Formatador` permanece **síncrono**: `formatar(resultado: ResultadoTool) -> str`.
