from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_DOWN
from uuid import uuid4

from app.models.enums import CategoriaEnum, FormaPagamentoEnum, StatusEnum
from app.repositories.dtos import TransacaoCreate
from app.services.confirmacao_state import ConfirmacaoState, EstadoConfirmacao
from app.services.parcelas import datas_do_grupo, status_por_data


@dataclass
class ResultadoCadastro:
    aguarda_confirmacao: bool = False
    pergunta: str | None = None
    transacoes: list = field(default_factory=list)
    mensagem_resposta: str = ""


@dataclass
class ResultadoCadastroLote:
    transacoes: list = field(default_factory=list)


def _valores_das_parcelas(
    valor_total: Decimal, valor_por_parcela: Decimal | None, parcela_total: int
) -> list[Decimal]:
    """Valor de cada parcela: se o usuário informou o valor da parcela, todas o
    recebem; senão divide o total com o resto absorvido na última."""
    if valor_por_parcela is not None:
        return [Decimal(str(valor_por_parcela))] * parcela_total
    base = (valor_total / parcela_total).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return [base] * (parcela_total - 1) + [valor_total - base * (parcela_total - 1)]


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

    async def executar_lote(self, mensagem: str, extrator_lista) -> "ResultadoCadastroLote":
        extracao = await extrator_lista.extrair(mensagem, date.today())
        hoje = date.today()
        lote_total = []
        for item in extracao.itens:
            grupo_parcela_id = uuid4()
            categoria = (
                CategoriaEnum.PARCELAMENTOS if item.parcela_total > 1 else CategoriaEnum(item.categoria)
            )
            embedding = await self._embedder.gerar_para_transacao(
                item.tipo, categoria, item.descricao, item.data
            )
            datas = datas_do_grupo(item.data, item.parcela_numero, item.parcela_total)
            for i, data_parcela in enumerate(datas):
                lote_total.append(
                    TransacaoCreate(
                        tipo=item.tipo,
                        valor=item.valor,
                        descricao=item.descricao,
                        categoria=categoria,
                        data=data_parcela,
                        parcela_numero=i + 1,
                        parcela_total=item.parcela_total,
                        grupo_parcela_id=grupo_parcela_id,
                        embedding=embedding,
                        status=status_por_data(data_parcela, hoje),
                    )
                )
        transacoes = await self._repository.criar_lote(lote_total)
        return ResultadoCadastroLote(transacoes=transacoes)

    async def executar_com_parcelas_confirmadas(
        self, mensagem_original: str, parcela_total: int, numero: str
    ) -> ResultadoCadastro:
        extracao = await self._extrator.extrair(mensagem_original, date.today())
        resultado = await self._processar(extracao, parcela_total, numero)
        self._confirmacao_state.limpar(numero)
        return resultado

    async def _processar(self, extracao, parcela_total: int, numero: str) -> ResultadoCadastro:
        hoje = date.today()
        valor_total = Decimal(str(extracao.valor_total))

        if parcela_total > 1:
            categoria = CategoriaEnum.PARCELAMENTOS
        elif extracao.tipo == "RECEITA":
            categoria = CategoriaEnum.RECEITA
        else:
            categorizacao = await self._categorizador.categorizar(
                extracao.tipo, extracao.descricao, float(valor_total)
            )
            categoria = CategoriaEnum(categorizacao.categoria)

        valores = _valores_das_parcelas(valor_total, extracao.valor_por_parcela, parcela_total)

        parcela_atual = extracao.parcela_atual
        if not 1 <= parcela_atual <= parcela_total:
            parcela_atual = 1
        datas = datas_do_grupo(extracao.data_referencia, parcela_atual, parcela_total)

        forma_pagamento = FormaPagamentoEnum(extracao.forma_pagamento)
        grupo_parcela_id = uuid4()

        embedding = await self._embedder.gerar_para_transacao(
            extracao.tipo, categoria, extracao.descricao, extracao.data_referencia
        )

        lote = []
        for i in range(parcela_total):
            data_parcela = datas[i]
            status = status_por_data(data_parcela, hoje)
            if parcela_total == 1 and forma_pagamento == FormaPagamentoEnum.PIX:
                status = StatusEnum.PAGO
            if extracao.tipo == "RECEITA" and data_parcela <= hoje:
                status = StatusEnum.PAGO
            lote.append(
                TransacaoCreate(
                    tipo=extracao.tipo,
                    valor=valores[i],
                    descricao=extracao.descricao,
                    categoria=categoria,
                    data=data_parcela,
                    parcela_numero=i + 1,
                    parcela_total=parcela_total,
                    grupo_parcela_id=grupo_parcela_id,
                    embedding=embedding,
                    status=status,
                    forma_pagamento=forma_pagamento,
                    responsavel=extracao.responsavel,
                    detalhes=extracao.detalhes,
                )
            )

        transacoes = await self._repository.criar_lote(lote)

        if parcela_total == 1:
            mensagem = f"Registrado: {extracao.descricao or extracao.tipo} — R$ {valor_total:.2f}"
        else:
            pagas = sum(1 for t in lote if t.status == StatusEnum.PAGO)
            mensagem = (
                f"Registrado: {extracao.descricao or extracao.tipo} — "
                f"{parcela_total} parcelas de R$ {valores[0]:.2f} registradas"
            )
            if pagas:
                sufixo = "s" if pagas > 1 else ""
                mensagem += f" ({pagas} já paga{sufixo})"

        return ResultadoCadastro(transacoes=transacoes, mensagem_resposta=mensagem)
