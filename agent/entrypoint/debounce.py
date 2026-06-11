import asyncio
from typing import Callable


class MessageDebouncer:
    def __init__(self) -> None:
        self._timers: dict[str, asyncio.TimerHandle] = {}
        self._buffers: dict[str, list[str]] = {}

    async def receber(self, numero: str, texto: str, callback: Callable) -> None:
        self._buffers.setdefault(numero, []).append(texto)
        if numero in self._timers:
            self._timers[numero].cancel()
        loop = asyncio.get_running_loop()
        self._timers[numero] = loop.call_later(10, self._disparar, numero, callback)

    def _disparar(self, numero: str, callback: Callable) -> None:
        texto_acumulado = " ".join(self._buffers.pop(numero, []))
        self._timers.pop(numero, None)
        asyncio.ensure_future(callback(numero, texto_acumulado))
