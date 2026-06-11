from datetime import date, datetime
from langchain_openai import ChatOpenAI
from pathlib import Path


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


def carregar_prompt(nome: str) -> str:
    return (Path(__file__).parents[2] / "prompts" / nome).read_text(encoding="utf-8")


def criar_llm(temperatura: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=temperatura)


def criar_llm_formatacao() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", temperature=0.3)
