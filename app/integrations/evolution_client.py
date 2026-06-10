import logging
import httpx


class EvolutionApiClient:
    def __init__(self, base_url: str, instance: str, api_key: str):
        self._base_url = base_url
        self._instance = instance
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    async def enviar_mensagem(self, numero: str, texto: str) -> None:
        url = f"{self._base_url}/message/sendText/{self._instance}"
        payload = {"number": numero, "text": texto}
        headers = {"apikey": self._api_key}
        try:
            await self._client.post(url, json=payload, headers=headers)
        except Exception as exc:
            logging.error("Falha ao enviar mensagem via Evolution API: %s", exc)

    async def fechar(self) -> None:
        await self._client.aclose()
