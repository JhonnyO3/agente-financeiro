from uuid import UUID

from app.agents.embedder import Embedder
from app.repositories.transacao_repository import TransacaoRepository
from app.services.confirmacao_state import ConfirmacaoState, EstadoConfirmacao

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


class ExcluirService:
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
        grupo_id = UUID(transacao.grupo_parcela_id) if isinstance(transacao.grupo_parcela_id, str) else transacao.grupo_parcela_id
        if transacao.parcela_total > 1:
            estado = EstadoConfirmacao(
                acao="EXCLUIR",
                transacao_id=transacao.id,
                grupo_parcela_id=grupo_id,
                pergunta_grupo=True,
            )
            self._confirmacao_state.salvar(numero, estado)
            pergunta = f"Deseja excluir só esta parcela ou todas as {transacao.parcela_total} parcelas?\n\n(parcela / grupo)"
            return _formatar_card(transacao, pergunta)
        estado = EstadoConfirmacao(
            acao="EXCLUIR",
            transacao_id=transacao.id,
            grupo_parcela_id=grupo_id,
            pergunta_grupo=False,
        )
        self._confirmacao_state.salvar(numero, estado)
        pergunta = "Confirma a exclusão deste lançamento? (sim / não)"
        return _formatar_card(transacao, pergunta)

    async def confirmar(self, numero: str, resposta_tipo: str) -> str:
        estado = self._confirmacao_state.obter(numero)
        if estado is None:
            return "Não há nenhuma exclusão pendente para confirmar."
        if estado.pergunta_grupo and resposta_tipo not in ("parcela", "grupo"):
            return "Por favor, responda 'parcela' para excluir só esta ou 'grupo' para excluir todas."
        self._confirmacao_state.limpar(numero)
        if resposta_tipo == "nao":
            return "Exclusão cancelada."
        if resposta_tipo == "parcela":
            await self._repository.excluir(estado.transacao_id)
            return "Parcela excluída com sucesso!"
        if resposta_tipo == "grupo":
            await self._repository.excluir_grupo(estado.grupo_parcela_id)
            return "Todas as parcelas foram excluídas com sucesso!"
        if resposta_tipo == "sim":
            await self._repository.excluir(estado.transacao_id)
            return "Lançamento excluído com sucesso!"
        return "Resposta não reconhecida. Exclusão cancelada."
