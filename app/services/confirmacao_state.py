from dataclasses import dataclass, field
from uuid import UUID
from datetime import datetime, timedelta
from typing import Literal
from app.repositories.dtos import TransacaoUpdate


@dataclass
class EstadoConfirmacao:
    acao: Literal["ALTERAR", "EXCLUIR", "AGUARDAR_PARCELAS"]
    transacao_id: int | None = None
    grupo_parcela_id: UUID | None = None
    novos_dados: TransacaoUpdate | None = None
    pergunta_grupo: bool = False
    mensagem_original: str = ""
    criado_em: datetime = field(default_factory=datetime.now)


class ConfirmacaoState:
    def __init__(self, ttl_minutos: int = 5):
        self._ttl = timedelta(minutes=ttl_minutos)
        self._store: dict[str, EstadoConfirmacao] = {}

    def salvar(self, numero: str, estado: EstadoConfirmacao) -> None:
        self._store[numero] = estado

    def obter(self, numero: str) -> EstadoConfirmacao | None:
        estado = self._store.get(numero)
        if estado is None:
            return None
        if datetime.now() - estado.criado_em > self._ttl:
            del self._store[numero]
            return None
        return estado

    def limpar(self, numero: str) -> None:
        self._store.pop(numero, None)
