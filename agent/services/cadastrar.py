from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_DOWN
from uuid import uuid4

from backend.models.enums import CategoriaEnum, FormaPagamentoEnum, StatusEnum
from backend.repositories.dtos import TransacaoCreate
from agent.services.confirmacao_state import ConfirmacaoState, EstadoConfirmacao
from agent.services.parcelas import (
    adicionar_meses,
    datas_do_grupo,
    data_status_por_forma,
    status_por_data,
)

_FORMAS_A_PRAZO = {FormaPagamentoEnum.CARTAO_CREDITO, FormaPagamentoEnum.BOLETO}


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

        categoria = await self._categoria(extracao, extracao.parcela_total)

        if categoria == CategoriaEnum.GASTOS_FIXOS and extracao.parcela_total == 1:
            self._confirmacao_state.salvar(
                numero,
                EstadoConfirmacao(acao="AGUARDAR_RECORRENCIA", mensagem_original=mensagem),
            )
            return ResultadoCadastro(
                aguarda_confirmacao=True,
                pergunta="Esse é um gasto fixo. Posso considerar que ele se repete todo mês?",
            )

        return await self._processar(extracao, extracao.parcela_total, categoria=categoria)

    async def executar_lote(self, mensagem: str, extrator_lista) -> "ResultadoCadastroLote":
        extracao = await extrator_lista.extrair(mensagem, date.today())
        hoje = date.today()
        lote_total = []
        for item in extracao.itens:
            grupo_parcela_id = uuid4()
            if item.tipo == "RECEITA":
                categoria = CategoriaEnum.RECEITA
            elif item.tipo == "INVESTIMENTO":
                categoria = CategoriaEnum.INVESTIMENTO
            else:
                categoria = CategoriaEnum(item.categoria)
            embedding = await self._embedder.gerar_para_transacao(
                item.tipo, categoria, item.descricao, item.data
            )
            datas = datas_do_grupo(item.data, item.parcela_numero, item.parcela_total)
            for i, data_parcela in enumerate(datas):
                status = status_por_data(data_parcela, hoje)
                if item.tipo == "RECEITA" and data_parcela <= hoje:
                    status = StatusEnum.PAGO
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
                        status=status,
                    )
                )
        transacoes = await self._repository.criar_lote(lote_total)
        return ResultadoCadastroLote(transacoes=transacoes)

    async def executar_com_parcelas_confirmadas(
        self, mensagem_original: str, parcela_total: int, numero: str
    ) -> ResultadoCadastro:
        extracao = await self._extrator.extrair(mensagem_original, date.today())
        categoria = await self._categoria(extracao, parcela_total)
        resultado = await self._processar(extracao, parcela_total, categoria=categoria)
        self._confirmacao_state.limpar(numero)
        return resultado

    async def executar_com_recorrencia_confirmada(
        self, mensagem_original: str, recorrente: bool, numero: str
    ) -> ResultadoCadastro:
        extracao = await self._extrator.extrair(mensagem_original, date.today())
        resultado = await self._processar(
            extracao, 1, categoria=CategoriaEnum.GASTOS_FIXOS, recorrente=recorrente
        )
        self._confirmacao_state.limpar(numero)
        return resultado

    async def _categoria(self, extracao, parcela_total: int) -> CategoriaEnum:
        if extracao.tipo == "RECEITA":
            return CategoriaEnum.RECEITA
        categorizacao = await self._categorizador.categorizar(
            extracao.tipo, extracao.descricao, float(Decimal(str(extracao.valor_total)))
        )
        return CategoriaEnum(categorizacao.categoria)

    async def _processar(
        self,
        extracao,
        parcela_total: int,
        categoria: CategoriaEnum,
        recorrente: bool = False,
    ) -> ResultadoCadastro:
        hoje = date.today()
        valor_total = Decimal(str(extracao.valor_total))

        if parcela_total > 1:
            forma_pagamento = FormaPagamentoEnum.CARTAO_CREDITO
        else:
            forma_pagamento = FormaPagamentoEnum(extracao.forma_pagamento)

        valores = _valores_das_parcelas(valor_total, extracao.valor_por_parcela, parcela_total)

        parcela_atual = extracao.parcela_atual
        if not 1 <= parcela_atual <= parcela_total:
            parcela_atual = 1

        data_base = extracao.data_referencia
        if forma_pagamento in _FORMAS_A_PRAZO:
            data_base = adicionar_meses(data_base, 1)
        datas = datas_do_grupo(data_base, parcela_atual, parcela_total)

        grupo_parcela_id = uuid4()

        embedding = await self._embedder.gerar_para_transacao(
            extracao.tipo, categoria, extracao.descricao, extracao.data_referencia
        )

        lote = []
        for i in range(parcela_total):
            data_parcela = datas[i]
            if extracao.tipo == "RECEITA":
                status = StatusEnum.PAGO if data_parcela <= hoje else StatusEnum.PENDENTE
            elif parcela_total == 1:
                _, status = data_status_por_forma(extracao.data_referencia, forma_pagamento)
            else:
                status = status_por_data(data_parcela, hoje)
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
                    recorrente=recorrente,
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
