from enum import Enum
from dataclasses import dataclass, field

from agent.config import settings


class Faixa(str, Enum):
    MATCH = "match"
    AMBIGUO = "ambiguo"
    PISO = "piso"


@dataclass
class ResultadoBusca:
    faixa: Faixa
    candidatos: list[tuple] = field(default_factory=list)


class BuscaRAG:
    def __init__(self, embedder, adapter) -> None:
        self._embedder = embedder
        self._adapter = adapter

    async def buscar(self, referencia: str, usuario_id: int) -> ResultadoBusca:
        embedding = await self._embedder.embedar(referencia)

        raw = await self._adapter.buscar_semantico_multiplos_com_distancia(
            embedding, limite=settings.RAG_MAX_OPCOES
        )

        # ordena por distância crescente
        candidatos: list[tuple] = sorted(raw, key=lambda t: t[1])

        # filtra abaixo do piso (distância < piso, excluindo igual)
        abaixo = [(tx, d) for tx, d in candidatos if d < settings.RAG_PISO]

        if not abaixo:
            return ResultadoBusca(faixa=Faixa.PISO, candidatos=[])

        melhor_dist = abaixo[0][1]
        if len(abaixo) >= 2:
            gap = abaixo[1][1] - melhor_dist
        else:
            # único candidato abaixo do piso — gap infinito
            gap = float("inf")

        if gap >= settings.RAG_MARGEM:
            return ResultadoBusca(faixa=Faixa.MATCH, candidatos=[abaixo[0]])

        truncado = abaixo[: settings.RAG_MAX_OPCOES]
        return ResultadoBusca(faixa=Faixa.AMBIGUO, candidatos=truncado)
