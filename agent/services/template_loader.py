from pathlib import Path

from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).parents[1] / "templates"

_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=False,
    autoescape=False,
)


def carregar_template(nome: str) -> str:
    """Carrega e retorna o conteúdo bruto do template `agent/templates/<nome>`."""
    source, _, _ = _env.loader.get_source(_env, nome)  # type: ignore[union-attr]
    return source


def renderizar(nome: str, contexto: dict) -> str:
    """Carrega o template `<nome>` e renderiza com o contexto fornecido."""
    tmpl = _env.get_template(nome)
    return tmpl.render(**contexto)
