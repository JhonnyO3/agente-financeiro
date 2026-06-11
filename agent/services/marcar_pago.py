from agent.agents.embedder import Embedder
from backend.models.enums import StatusEnum
from backend.repositories.dtos import TransacaoUpdate
from backend.repositories.transacao_repository import TransacaoRepository
from agent.services.confirmacao_state import ConfirmacaoState, EstadoConfirmacao

_NAO_ENCONTRADO = "Não encontrei nenhum registro parecido com o que você descreveu. Pode detalhar mais?"


def _formatar_card(transacao, pergunta: str) -> str:
    data_str = transacao.data.strftime("%d/%m/%Y")
    valor_str = f"{transacao.valor:.2f}"
    parcela_label = ""
    if transacao.parcela_total > 1:
        parcela_label = f"(Parcela {transacao.parcela_numero}/{transacao.parcela_total})"
    descricao = transacao.descricao or ""
    categoria = transacao.categoria.value if hasattr(transacao.categoria, "value") else str(transacao.categoria)
    linhas = [
        "Encontrei este registro:",
        "",
        f"📅 {data_str}",
        f"💰 R$ {valor_str} {parcela_label}".rstrip(),
        f"🏷️ {categoria}",
        f"📝 {descricao}",
        "",
        pergunta,
    ]
    return "\n".join(linhas)


class MarcarPagoService:
    def __init__(
        self,
        repository: TransacaoRepository,
        embedder: Embedder,
        confirmacao_state: ConfirmacaoState,
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._confirmacao_state = confirmacao_state

    async def iniciar(self, mensagem: str, numero: str) -> str:
        vetor = await self._embedder.gerar(mensagem)
        resultado = await self._repository.buscar_semantico_com_distancia(vetor, limite=1)
        if resultado is None:
            return _NAO_ENCONTRADO
        transacao, distancia = resultado
        if distancia > 1.0:
            return _NAO_ENCONTRADO
        estado = EstadoConfirmacao(
            acao="MARCAR_PAGO",
            transacao_id=transacao.id,
        )
        self._confirmacao_state.salvar(numero, estado)
        pergunta = "Confirma marcar como PAGO? (sim / não)"
        return _formatar_card(transacao, pergunta)

    async def confirmar(self, numero: str, confirmado: bool) -> str:
        estado = self._confirmacao_state.obter(numero)
        if estado is None:
            return "Não há nenhuma marcação pendente para confirmar."
        self._confirmacao_state.limpar(numero)
        if not confirmado:
            return "Operação cancelada."
        await self._repository.atualizar(estado.transacao_id, TransacaoUpdate(status=StatusEnum.PAGO))
        return "Lançamento marcado como pago!"
