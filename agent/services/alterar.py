from datetime import date

from agent.agents.embedder import Embedder
from agent.agents.extrator_alteracao import ExtratorAlteracao
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


def _extrair_update(extracao) -> TransacaoUpdate:
    return TransacaoUpdate(
        tipo=None,
        valor=extracao.novo_valor,
        descricao=extracao.nova_descricao,
        categoria=extracao.nova_categoria,
        data=extracao.nova_data,
    )


class AlterarService:
    def __init__(
        self,
        repository: TransacaoRepository,
        embedder: Embedder,
        extrator_alteracao: ExtratorAlteracao,
        confirmacao_state: ConfirmacaoState,
    ) -> None:
        self._repository = repository
        self._embedder = embedder
        self._extrator_alteracao = extrator_alteracao
        self._confirmacao_state = confirmacao_state

    async def iniciar(self, mensagem: str, numero: str) -> str:
        extracao = await self._extrator_alteracao.extrair(mensagem, date.today())
        vetor = await self._embedder.gerar(mensagem)
        resultado = await self._repository.buscar_semantico_com_distancia(vetor, limite=1)
        if resultado is None:
            return _NAO_ENCONTRADO
        transacao, distancia = resultado
        if distancia > 1.0:
            return _NAO_ENCONTRADO
        update = _extrair_update(extracao)
        estado = EstadoConfirmacao(
            acao="ALTERAR",
            transacao_id=transacao.id,
            novos_dados=update,
        )
        self._confirmacao_state.salvar(numero, estado)
        campos_novos = {
            k: v
            for k, v in [
                ("valor", extracao.novo_valor),
                ("descrição", extracao.nova_descricao),
                ("categoria", extracao.nova_categoria),
                ("data", extracao.nova_data),
            ]
            if v is not None
        }
        novos_str = ", ".join(f"{k}: {v}" for k, v in campos_novos.items()) if campos_novos else "sem alterações detectadas"
        pergunta = f"Deseja alterar este lançamento com os novos dados: {novos_str}?\n\nConfirma? (sim / não)"
        return _formatar_card(transacao, pergunta)

    async def confirmar(self, numero: str, confirmado: bool) -> str:
        estado = self._confirmacao_state.obter(numero)
        if estado is None:
            return "Não há nenhuma alteração pendente para confirmar."
        self._confirmacao_state.limpar(numero)
        if not confirmado:
            return "Alteração cancelada."
        await self._repository.atualizar(estado.transacao_id, estado.novos_dados)
        return "Lançamento alterado com sucesso!"
