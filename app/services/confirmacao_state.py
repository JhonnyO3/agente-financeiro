from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from app.repositories.dtos import TransacaoUpdate

TTL_SEGUNDOS = 300

_UTC = timezone.utc


def _now() -> datetime:
    return datetime.now(_UTC)


@dataclass
class EstadoConfirmacao:
    acao: Literal["ALTERAR", "EXCLUIR", "AGUARDAR_PARCELAS"]
    transacao_id: int | None = None
    grupo_parcela_id: UUID | None = None
    novos_dados: TransacaoUpdate | None = None
    pergunta_grupo: bool = False
    mensagem_original: str = ""


class ConfirmacaoState:
    def __init__(self) -> None:
        self._estados: dict[str, EstadoConfirmacao] = {}
        self._timestamps: dict[str, datetime] = {}

    def salvar(self, numero: str, estado: EstadoConfirmacao) -> None:
        self._estados[numero] = estado
        self._timestamps[numero] = _now()

    def obter(self, numero: str) -> EstadoConfirmacao | None:
        estado = self._estados.get(numero)
        if estado is None:
            return None
        criado = self._timestamps.get(numero, _now())
        if _now() - criado > timedelta(seconds=TTL_SEGUNDOS):
            self.limpar(numero)
            return None
        return estado

    def limpar(self, numero: str) -> None:
        self._estados.pop(numero, None)
        self._timestamps.pop(numero, None)
