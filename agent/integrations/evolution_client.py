import asyncio
import logging
import httpx

_MAX_TENTATIVAS = 3
_BACKOFF_BASE = 1.0  # segundos


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
        last_exc: Exception | None = None

        for tentativa in range(_MAX_TENTATIVAS):
            try:
                resp = await self._client.post(url, json=payload, headers=headers)
                if 400 <= resp.status_code < 500:
                    resp.raise_for_status()
                if resp.status_code >= 500:
                    exc = httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    last_exc = exc
                    if tentativa < _MAX_TENTATIVAS - 1:
                        await asyncio.sleep(_BACKOFF_BASE * (2**tentativa))
                    continue
                return
            except (httpx.HTTPStatusError,) as exc:
                # 4xx — propaga imediatamente sem retry
                raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                logging.warning(
                    "Timeout/transporte na tentativa %d: %s", tentativa + 1, exc
                )
                if tentativa < _MAX_TENTATIVAS - 1:
                    await asyncio.sleep(_BACKOFF_BASE * (2**tentativa))

        assert last_exc is not None
        raise last_exc

    async def fechar(self) -> None:
        await self._client.aclose()
