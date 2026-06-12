from pathlib import Path

from agent.config import settings

ARQUIVO_POR_ACAO = {
    "classificador": "01-classificador.md",
    "cadastrar": "02-extracao-cadastrar.md",
    "atualizar": "03-extracao-atualizar.md",
    "conversar": "06-conversar.md",
}

_PROMPTS_DIR = Path(__file__).parents[1] / "prompts"


def _carregar(nome: str) -> str:
    return (_PROMPTS_DIR / nome).read_text(encoding="utf-8")


def montar_prompt(acao: str, contexto: dict) -> str:
    ctx = dict(contexto)
    if "responsavel_padrao" not in ctx:
        ctx["responsavel_padrao"] = settings.RESPONSAVEL_PADRAO

    base = _carregar("00-base.md")
    injection_raw = _carregar(ARQUIVO_POR_ACAO[acao])

    try:
        injection = injection_raw.format(**ctx)
    except KeyError as exc:
        raise KeyError(f"Variável obrigatória ausente no contexto: {exc}") from exc

    try:
        return base.format(injection_acao=injection, **ctx)
    except KeyError as exc:
        raise KeyError(f"Variável obrigatória ausente no contexto: {exc}") from exc
