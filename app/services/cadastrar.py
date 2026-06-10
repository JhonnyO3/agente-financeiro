from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN
from uuid import uuid4

from app.repositories.dtos import TransacaoCreate
from app.services.confirmacao_state import ConfirmacaoState, EstadoConfirmacao


@dataclass
class ResultadoCadastro:
    aguarda_confirmacao: bool = False
    pergunta: str | None = None
    transacoes: list = field(default_factory=list)
    mensagem_resposta: str = ""


class CadastrarService:
    def __init__(self, repository, embedder, extrator, categorizador, confirmacao_state: ConfirmacaoState):
        self._repository = repository
        self._embedder = embedder
        self._extrator = extrator
        self._categorizador = categorizador
        self._confirmacao_state = confirmacao_state

    async def executar(self, mensagem: str, numero: str) -> ResultadoCadastro:
        extracao = await self._extrator.extrair(mensagem, date.today())

        if extracao.menciona_cartao and extracao.parcela_total == 1:
            self._confirmacao_state.salvar(
                numero,
                EstadoConfirmacao(acao="AGUARDAR_PARCELAS", mensagem_original=mensagem),
            )
            return ResultadoCadastro(
                aguarda_confirmacao=True,
                pergunta="É à vista ou parcelado? Se parcelado, quantas vezes?",
            )

        return await self._processar(extracao, extracao.parcela_total, numero)

    async def executar_com_parcelas_confirmadas(
        self, mensagem_original: str, parcela_total: int, numero: str
    ) -> ResultadoCadastro:
        extracao = await self._extrator.extrair(mensagem_original, date.today())
        resultado = await self._processar(extracao, parcela_total, numero)
        self._confirmacao_state.limpar(numero)
        return resultado

    async def _processar(self, extracao, parcela_total: int, numero: str) -> ResultadoCadastro:
        categorizacao = await self._categorizador.categorizar(
            extracao.tipo, extracao.descricao, float(extracao.valor_total)
        )

        valor_total = Decimal(str(extracao.valor_total))
        valor_por_parcela = (valor_total / parcela_total).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        ultimo_valor = valor_total - valor_por_parcela * (parcela_total - 1)

        grupo_parcela_id = uuid4()
        data_base = extracao.data_referencia

        embedding = await self._embedder.gerar_para_transacao(
            extracao.tipo, categorizacao.categoria, extracao.descricao, data_base
        )

        lote = []
        for i in range(parcela_total):
            valor = ultimo_valor if i == parcela_total - 1 else valor_por_parcela
            data_parcela = data_base + timedelta(days=30 * i)
            lote.append(
                TransacaoCreate(
                    tipo=extracao.tipo,
                    valor=valor,
                    descricao=extracao.descricao,
                    categoria=categorizacao.categoria,
                    data=data_parcela,
                    parcela_numero=i + 1,
                    parcela_total=parcela_total,
                    grupo_parcela_id=grupo_parcela_id,
                    embedding=embedding,
                )
            )

        transacoes = await self._repository.criar_lote(lote)

        if parcela_total == 1:
            mensagem = f"Registrado: {extracao.descricao or extracao.tipo} — R$ {valor_total:.2f}"
        else:
            mensagem = (
                f"Registrado: {extracao.descricao or extracao.tipo} — "
                f"{parcela_total}x de R$ {valor_por_parcela:.2f}"
            )

        return ResultadoCadastro(transacoes=transacoes, mensagem_resposta=mensagem)
