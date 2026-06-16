"""
Worker: fila por usuário + micro-debounce + pipeline completo (multi-usuário).

Recebe mensagens via Worker.receber() e as processa com
Worker.processar_pendentes() após a janela de debounce.

Conforme contrato worker-pipeline.md (congelado).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from agent.domain.estado import Mensagem
from agent.services.estado_store import resumir_pendencia

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        classificador: Any,
        formatador: Any,
        evolution_client: Any,
        estado_store: Any,
        construir_roteador: Callable[[Any], Any],
        repo_factory: Callable[[int], Any] | None = None,
        debounce_segundos: int | float = 5,
    ) -> None:
        self._classificador = classificador
        self._formatador = formatador
        self._evolution = evolution_client
        self._estado_store = estado_store
        self._construir_roteador = construir_roteador
        self._repo_factory = repo_factory
        self._debounce = debounce_segundos

        # numero → (usuario_id, lista de fragmentos pendentes)
        self._pendentes: dict[str, tuple[int, list[str]]] = {}
        # numero → lock para serializar processamento por número de origem
        self._locks: dict[str, asyncio.Lock] = {}

    def _lock_para(self, numero: str) -> asyncio.Lock:
        if numero not in self._locks:
            self._locks[numero] = asyncio.Lock()
        return self._locks[numero]

    async def receber(self, usuario_id: int, numero: str, texto: str) -> None:
        """Acumula fragmento na fila do usuário identificado por numero."""
        async with self._lock_para(numero):
            if numero not in self._pendentes:
                self._pendentes[numero] = (usuario_id, [])
            uid, fragmentos = self._pendentes[numero]
            fragmentos.append(texto)
            self._pendentes[numero] = (uid, fragmentos)

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
                entrada = self._pendentes.pop(numero, None)
            if entrada is None:
                continue
            usuario_id, fragmentos = entrada
            if not fragmentos:
                continue
            texto = "\n".join(fragmentos)
            await self._processar(usuario_id, numero, texto)

    async def _processar(self, usuario_id: int, numero: str, texto: str) -> None:
        try:
            agora = datetime.now(timezone.utc)

            # 1. Carrega estado ANTES de classificar (corrige bug histórico vazio)
            estado = await self._estado_store.obter(usuario_id, agora)

            # 2. Registra mensagem do usuário no histórico
            msg_usuario = Mensagem(papel="usuario", texto=texto, em=agora)
            await self._estado_store.registrar_mensagem(usuario_id, msg_usuario, agora)

            # 3. Classifica COM histórico anterior + pendência resumida
            intencao = await self._classificador.classificar(
                mensagem=texto,
                historico=[f"{m.papel}: {m.texto}" for m in estado.historico],
                estado_pendente=resumir_pendencia(estado),
            )

            # 4. Repo por mensagem + roteador escopado por mensagem
            if self._repo_factory is not None:
                repo = self._repo_factory(usuario_id)
            else:
                repo = None
            roteador = self._construir_roteador(repo)
            resultado = await roteador.rotear(
                intencao, usuario_id, agora, {"mensagem": texto}
            )

            # 5. Formata, registra resposta e envia
            resposta = self._formatador.formatar(resultado)
            msg_assistente = Mensagem(papel="assistente", texto=resposta, em=agora)
            await self._estado_store.registrar_mensagem(
                usuario_id, msg_assistente, agora
            )
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
