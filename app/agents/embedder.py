from datetime import date
from langchain_openai import OpenAIEmbeddings


class Embedder:
    def __init__(self):
        self._client = OpenAIEmbeddings(model="text-embedding-3-small")

    async def gerar(self, texto: str) -> list[float]:
        return await self._client.aembed_query(texto)

    async def gerar_para_transacao(
        self, tipo: str, categoria: str, descricao: str | None, data: date
    ) -> list[float]:
        partes = [tipo, categoria]
        if descricao:
            partes.append(descricao)
        partes.append(data.strftime("%d/%m/%Y"))
        texto = " ".join(partes)
        return await self.gerar(texto)
