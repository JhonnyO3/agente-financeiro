from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Protocol

from langchain_core.messages import HumanMessage

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger(__name__)

_BUFFER_KEY = "chat:{numero}:buffer"


class _RedisClient(Protocol):
    async def rpush(self, key: str, *values: str) -> int: ...
    async def lrange(self, key: str, start: int, end: int) -> list[bytes]: ...
    async def delete(self, key: str) -> int: ...


class Consumer:
    def __init__(
        self,
        fila: asyncio.Queue,
        graph: CompiledStateGraph,
        redis_client: _RedisClient,
        debounce_segundos: int | float = 5,
    ) -> None:
        self._fila = fila
        self._graph = graph
        self._redis = redis_client
        self._debounce = debounce_segundos
        self._task: asyncio.Task | None = None
        self._timers: dict[str, asyncio.Task] = {}

    def iniciar(self) -> None:
        self._task = asyncio.create_task(self._loop())

    def parar(self) -> None:
        if self._task:
            self._task.cancel()

    async def _loop(self) -> None:
        while True:
            usuario_id, numero, texto = await self._fila.get()
            try:
                await self._receber(usuario_id, numero, texto)
            except Exception:
                logger.exception("erro ao enfileirar mensagem usuario_id=%s", usuario_id)
            finally:
                self._fila.task_done()

    async def _receber(self, usuario_id: int, numero: str, texto: str) -> None:
        await self._redis.rpush(_BUFFER_KEY.format(numero=numero), texto)

        if numero in self._timers:
            self._timers[numero].cancel()

        self._timers[numero] = asyncio.create_task(
            self._disparar(usuario_id, numero)
        )

    async def _disparar(self, usuario_id: int, numero: str) -> None:
        try:
            if self._debounce > 0:
                await asyncio.sleep(self._debounce)

            key = _BUFFER_KEY.format(numero=numero)
            fragmentos = await self._redis.lrange(key, 0, -1)
            await self._redis.delete(key)
            self._timers.pop(numero, None)

            if not fragmentos:
                return

            texto = "\n".join(
                f.decode("utf-8") if isinstance(f, bytes) else f for f in fragmentos
            )

            await self._graph.ainvoke(
                {
                    "messages": [HumanMessage(content=texto)],
                    "usuario_id": usuario_id,
                    "numero": numero,
                },
                config={"configurable": {"thread_id": numero}},
            )
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("erro ao processar mensagem para numero=%s", numero)
