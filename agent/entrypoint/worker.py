"""
Worker: fila por usuário + micro-debounce + pipeline completo.

Recebe mensagens via Worker.receber() e as processa com
Worker.processar_pendentes() após a janela de debounce.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from agent.domain.estado import Mensagem

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        classificador: Any,
        roteador: Any,
        formatador: Any,
        evolution_client: Any,
        estado_store: Any,
        debounce_segundos: int | float = 5,
    ) -> None:
        self._classificador = classificador
        self._roteador = roteador
        self._formatador = formatador
        self._evolution = evolution_client
        self._estado_store = estado_store
        self._debounce = debounce_segundos

        # numero → lista de fragmentos pendentes
        self._pendentes: dict[str, list[str]] = {}
        # numero → lock para serializar processamento por usuário
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_para(self, numero: str) -> asyncio.Lock:
        if numero not in self._locks:
            self._locks[numero] = asyncio.Lock()
        return self._locks[numero]

    async def receber(self, numero: str, texto: str) -> None:
        """Acumula fragmento na fila do usuário."""
        async with self._lock_para(numero):
            if numero not in self._pendentes:
                self._pendentes[numero] = []
            self._pendentes[numero].append(texto)

    async def processar_pendentes(self) -> None:
        """
        Após a janela de debounce, processa cada usuário que tem mensagens pendentes.
        Para debounce_segundos=0 processa imediatamente (usado em testes).
        """
        if self._debounce > 0:
            await asyncio.sleep(self._debounce)

        numeros = list(self._pendentes.keys())
        for numero in numeros:
            async with self._lock_para(numero):
                fragmentos = self._pendentes.pop(numero, [])
            if not fragmentos:
                continue
            texto = "\n".join(fragmentos)
            await self._processar(numero, texto)

    async def _processar(self, numero: str, texto: str) -> None:
        try:
            agora = datetime.now(timezone.utc)

            # Registra mensagem do usuário
            msg_usuario = Mensagem(papel="usuario", texto=texto, em=agora)
            await self._estado_store.registrar_mensagem(numero, msg_usuario)

            # Pipeline
            intencao = await self._classificador.classificar(texto)
            resultado = await self._roteador.rotear(intencao)
            resposta = self._formatador.formatar(resultado)

            # Registra resposta do assistente
            msg_assistente = Mensagem(papel="assistente", texto=resposta, em=agora)
            await self._estado_store.registrar_mensagem(numero, msg_assistente)

            await self._evolution.enviar_mensagem(numero, resposta)

        except Exception:
            logger.exception("erro ao processar mensagem para %s", numero)
            mensagem_amigavel = (
                "Desculpe, ocorreu um problema ao processar sua mensagem. "
                "Por favor, tente novamente em instantes."
            )
            try:
                await self._evolution.enviar_mensagem(numero, mensagem_amigavel)
            except Exception:
                logger.exception("erro ao enviar mensagem de erro para %s", numero)
