from langchain_openai import ChatOpenAI
from pathlib import Path


def carregar_prompt(nome: str) -> str:
    return (Path(__file__).parents[2] / "prompts" / nome).read_text(encoding="utf-8")


def criar_llm(temperatura: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o-mini", temperature=temperatura)


def criar_llm_formatacao() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", temperature=0.3)
