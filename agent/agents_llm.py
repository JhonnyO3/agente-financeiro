import sys
from datetime import date, datetime
from pathlib import Path

from agent.config import settings

__all__ = ["carregar_prompt", "coagir_data", "criar_llm", "Embedder"]

# Importação protegida: não sobrescreve se já estiver no namespace (ex.: mock de teste)
if "ChatOpenAI" not in sys.modules[__name__].__dict__:
    from langchain_openai import ChatOpenAI  # noqa: F401

if "OpenAIEmbeddings" not in sys.modules[__name__].__dict__:
    from langchain_openai import OpenAIEmbeddings  # noqa: F401


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


class Embedder:
    """Gerador de embeddings usando text-embedding-3-small."""

    def __init__(self) -> None:
        _cls = sys.modules[__name__].__dict__["OpenAIEmbeddings"]
        self._client = _cls(model="text-embedding-3-small")

    async def gerar(self, texto: str) -> list[float]:
        return await self._client.aembed_query(texto)

    async def embedar(self, texto: str) -> list[float]:
        """Alias de gerar — usado pela BuscaRAG."""
        return await self.gerar(texto)

    async def gerar_para_transacao(
        self, tipo: str, categoria: str, descricao: str | None, data: date
    ) -> list[float]:
        partes = [tipo, categoria]
        if descricao:
            partes.append(descricao)
        partes.append(data.strftime("%d/%m/%Y"))
        texto = " ".join(partes)
        return await self.gerar(texto)
