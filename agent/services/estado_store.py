from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from agent.domain.estado import EstadoConversa, Mensagem

_MAX_HISTORICO = 5
_TTL_FISICO_S = 86400  # 24h


@runtime_checkable
class EstadoStore(Protocol):
    async def obter(self, usuario_id: int, agora: datetime) -> EstadoConversa: ...
    async def salvar(self, estado: EstadoConversa) -> None: ...
    async def limpar_pendencia(self, usuario_id: int) -> None: ...
    async def registrar_mensagem(
        self, usuario_id: int, msg: Mensagem, agora: datetime
    ) -> None: ...


def _limpar_expirados(estado: EstadoConversa, agora: datetime) -> EstadoConversa:
    pendencia_expirou = estado.expira_em is not None and agora > estado.expira_em
    historico_expirou = (
        estado.historico_expira_em is not None and agora > estado.historico_expira_em
    )
    update: dict[str, Any] = {}
    if pendencia_expirou:
        update["acao_pendente"] = None
        update["payload_pendente"] = None
        update["campos_faltantes"] = []
        update["opcoes"] = None
        update["expira_em"] = None
    if historico_expirou:
        update["historico"] = []
        update["historico_expira_em"] = None
    if update:
        return estado.model_copy(update=update)
    return estado


class EstadoStoreMemoria:
    def __init__(self) -> None:
        self._dados: dict[int, EstadoConversa] = {}

    async def obter(self, usuario_id: int, agora: datetime) -> EstadoConversa:
        estado = self._dados.get(usuario_id)
        if estado is None:
            return EstadoConversa(usuario_id=usuario_id)
        return _limpar_expirados(estado, agora)

    async def salvar(self, estado: EstadoConversa) -> None:
        self._dados[estado.usuario_id] = estado

    async def limpar_pendencia(self, usuario_id: int) -> None:
        estado = self._dados.get(usuario_id)
        if estado is None:
            return
        self._dados[usuario_id] = estado.model_copy(
            update={
                "acao_pendente": None,
                "payload_pendente": None,
                "campos_faltantes": [],
                "opcoes": None,
                "expira_em": None,
            }
        )

    async def registrar_mensagem(
        self, usuario_id: int, msg: Mensagem, agora: datetime
    ) -> None:
        estado = await self.obter(usuario_id=usuario_id, agora=agora)
        historico = list(estado.historico) + [msg]
        historico = historico[-_MAX_HISTORICO:]
        await self.salvar(estado.model_copy(update={"historico": historico}))


class EstadoStoreRedis:
    def __init__(self, client: Any) -> None:
        self._client = client

    def _chave(self, usuario_id: int) -> str:
        return f"estado:{usuario_id}"

    async def obter(self, usuario_id: int, agora: datetime) -> EstadoConversa:
        raw = await self._client.get(self._chave(usuario_id))
        if raw is None:
            return EstadoConversa(usuario_id=usuario_id)
        estado = EstadoConversa.model_validate_json(raw)
        return _limpar_expirados(estado, agora)

    async def salvar(self, estado: EstadoConversa) -> None:
        await self._client.setex(
            self._chave(estado.usuario_id),
            _TTL_FISICO_S,
            estado.model_dump_json(),
        )

    async def limpar_pendencia(self, usuario_id: int) -> None:
        raw = await self._client.get(self._chave(usuario_id))
        if raw is None:
            return
        estado = EstadoConversa.model_validate_json(raw)
        estado = estado.model_copy(
            update={
                "acao_pendente": None,
                "payload_pendente": None,
                "campos_faltantes": [],
                "opcoes": None,
                "expira_em": None,
            }
        )
        await self.salvar(estado)

    async def registrar_mensagem(
        self, usuario_id: int, msg: Mensagem, agora: datetime
    ) -> None:
        estado = await self.obter(usuario_id=usuario_id, agora=agora)
        historico = list(estado.historico) + [msg]
        historico = historico[-_MAX_HISTORICO:]
        await self.salvar(estado.model_copy(update={"historico": historico}))


def resumir_pendencia(estado: EstadoConversa) -> str:
    if estado.acao_pendente is None:
        return "nenhuma"

    acao = estado.acao_pendente

    if estado.opcoes is not None:
        n = len(estado.opcoes)
        # verificar se é escopo (opções com ref contendo "escopo")
        if any("escopo" in op.ref for op in estado.opcoes):
            return "exclusão aguardando escopo"
        return f"lista de {n} opções exibida"

    if acao == "cadastrar":
        if estado.campos_faltantes:
            campo = estado.campos_faltantes[0]
            return f"cadastro aguardando {campo}"
        return "cadastro aguardando confirmação"

    return f"{acao} pendente"
