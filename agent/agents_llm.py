import sys
from datetime import date, datetime
from pathlib import Path

from agent.config import settings
from agent.agents.embedder import Embedder  # reexport

__all__ = ["carregar_prompt", "coagir_data", "criar_llm", "Embedder"]

# Importação protegida: não sobrescreve se já estiver no namespace (ex.: mock de teste)
if "ChatOpenAI" not in sys.modules[__name__].__dict__:
    from langchain_openai import ChatOpenAI  # noqa: F401


def carregar_prompt(nome: str) -> str:
    return (Path(__file__).parent / "prompts" / nome).read_text(encoding="utf-8")


def coagir_data(valor):
    """Normaliza datas vindas do LLM: aceita date, datetime, ISO e DD/MM/YYYY."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        texto = valor.strip()
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
            try:
                return datetime.strptime(texto, formato).date()
            except ValueError:
                continue
    return valor


def criar_llm(temperatura: float = 0.0):
    _cls = sys.modules[__name__].__dict__["ChatOpenAI"]
    return _cls(model=settings.LLM_MODELO_CLASSIFICACAO, temperature=temperatura)


def criar_llm_formatacao():
    _cls = sys.modules[__name__].__dict__["ChatOpenAI"]
    return _cls(model=settings.LLM_MODELO_CONVERSAR, temperature=0.3)
