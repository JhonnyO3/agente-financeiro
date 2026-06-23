import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

_MAX_TENTATIVAS = 3
_BACKOFF_BASE = 1.0  # segundos


class EvolutionApiClient:
    def __init__(self, base_url: str, instance: str, api_key: str):
        self._base_url = base_url
        self._instance = instance
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    @staticmethod
    def _numero_com_ddi(numero: str) -> str:
        digitos = "".join(ch for ch in numero if ch.isdigit())
        if not digitos.startswith("55"):
            return "55" + digitos
        return digitos

    async def enviar_mensagem(self, numero: str, texto: str) -> None:
        url = f"{self._base_url}/message/sendText/{self._instance}"
        payload = {"number": self._numero_com_ddi(numero), "text": texto}
        headers = {"apikey": self._api_key}
        last_exc: Exception | None = None

        logger.info("evolution:enviar numero=%s chars=%d url=%s", numero, len(texto), url)
        for tentativa in range(_MAX_TENTATIVAS):
            try:
                resp = await self._client.post(url, json=payload, headers=headers)
                if 400 <= resp.status_code < 500:
                    logger.error("evolution:enviar 4xx numero=%s status=%d body=%s", numero, resp.status_code, resp.text[:200])
                    resp.raise_for_status()
                if resp.status_code >= 500:
                    logger.warning("evolution:enviar 5xx tentativa=%d numero=%s status=%d", tentativa + 1, numero, resp.status_code)
                    exc = httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    last_exc = exc
                    if tentativa < _MAX_TENTATIVAS - 1:
                        await asyncio.sleep(_BACKOFF_BASE * (2**tentativa))
                    continue
                logger.info("evolution:enviar ok numero=%s tentativa=%d", numero, tentativa + 1)
                return
            except (httpx.HTTPStatusError,) as exc:
                # 4xx — propaga imediatamente sem retry
                raise
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                logger.warning("evolution:enviar timeout/transporte tentativa=%d numero=%s erro=%s", tentativa + 1, numero, exc)
                if tentativa < _MAX_TENTATIVAS - 1:
                    await asyncio.sleep(_BACKOFF_BASE * (2**tentativa))

        assert last_exc is not None
        raise last_exc

    async def fechar(self) -> None:
        await self._client.aclose()
