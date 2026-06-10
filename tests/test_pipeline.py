import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.classificador import IntencaoResult
from app.agents.confirmacao_chain import ConfirmacaoResposta
from app.agents.extrator_parcelas import ExtratorParcelasResult
from app.services.cadastrar import ResultadoCadastro
from app.services.confirmacao_state import EstadoConfirmacao
from app.services.pipeline import Pipeline


def _make_pipeline(**overrides):
    classificador = AsyncMock()
    cadastrar = AsyncMock()
    alterar = AsyncMock()
    excluir = AsyncMock()
    marcar_pago = AsyncMock()
    consultar = AsyncMock()
    formatador = AsyncMock()
    confirmacao_state = MagicMock()
    confirmacao_chain = AsyncMock()
    extrator_parcelas = AsyncMock()
    extrator_exclusao_lote = AsyncMock()
    extrator_lista = AsyncMock()

    formatador.formatar = AsyncMock(return_value="resposta formatada")
    confirmacao_state.obter = MagicMock(return_value=None)

    deps = dict(
        classificador=classificador,
        cadastrar=cadastrar,
        alterar=alterar,
        excluir=excluir,
        marcar_pago=marcar_pago,
        consultar=consultar,
        formatador=formatador,
        confirmacao_state=confirmacao_state,
        confirmacao_chain=confirmacao_chain,
        extrator_parcelas=extrator_parcelas,
        extrator_exclusao_lote=extrator_exclusao_lote,
        extrator_lista=extrator_lista,
    )
    deps.update(overrides)

    pipeline = Pipeline(**deps)
    return pipeline, deps


@pytest.mark.asyncio
async def test_sem_estado_classificador_chamado():
    pipeline, deps = _make_pipeline()
    deps["classificador"].classificar = AsyncMock(
        return_value=IntencaoResult(intencao="FORA_DE_ESCOPO", confianca="alta")
    )

    await pipeline.processar("5511999999999", "mensagem qualquer")

    deps["classificador"].classificar.assert_called_once_with("mensagem qualquer")


@pytest.mark.asyncio
async def test_intencao_cadastrar_executa_e_formata():
    pipeline, deps = _make_pipeline()
    resultado_cadastro = ResultadoCadastro(transacoes=[MagicMock()], mensagem_resposta="ok")
    deps["classificador"].classificar = AsyncMock(
        return_value=IntencaoResult(intencao="CADASTRAR", confianca="alta")
    )
    deps["cadastrar"].executar = AsyncMock(return_value=resultado_cadastro)

    await pipeline.processar("5511999999999", "gastei 50 no almoço")

    deps["cadastrar"].executar.assert_called_once_with("gastei 50 no almoço", "5511999999999")
    deps["formatador"].formatar.assert_called_once_with(resultado_cadastro, "cadastro")


@pytest.mark.asyncio
async def test_intencao_fora_escopo_formata_com_fora_escopo():
    pipeline, deps = _make_pipeline()
    deps["classificador"].classificar = AsyncMock(
        return_value=IntencaoResult(intencao="FORA_DE_ESCOPO", confianca="alta")
    )

    await pipeline.processar("5511999999999", "qual o significado da vida?")

    deps["formatador"].formatar.assert_called_once()
    _, tipo = deps["formatador"].formatar.call_args[0]
    assert tipo == "fora_escopo"


@pytest.mark.asyncio
async def test_estado_aguardar_parcelas_extrai_e_executa_com_parcelas():
    estado = EstadoConfirmacao(
        acao="AGUARDAR_PARCELAS",
        mensagem_original="comprei celular no cartão",
    )
    pipeline, deps = _make_pipeline()
    deps["confirmacao_state"].obter = MagicMock(return_value=estado)
    deps["extrator_parcelas"].extrair = AsyncMock(
        return_value=ExtratorParcelasResult(parcela_total=3)
    )
    resultado_cadastro = ResultadoCadastro(transacoes=[MagicMock()], mensagem_resposta="ok")
    deps["cadastrar"].executar_com_parcelas_confirmadas = AsyncMock(return_value=resultado_cadastro)

    await pipeline.processar("5511999999999", "3 vezes")

    deps["extrator_parcelas"].extrair.assert_called_once_with("3 vezes")
    deps["cadastrar"].executar_com_parcelas_confirmadas.assert_called_once_with(
        "comprei celular no cartão", 3, "5511999999999"
    )
    deps["formatador"].formatar.assert_called_once_with(resultado_cadastro, "cadastro")


@pytest.mark.asyncio
async def test_estado_alterar_sim_confirma_com_true():
    estado = EstadoConfirmacao(acao="ALTERAR", pergunta_grupo=False)
    pipeline, deps = _make_pipeline()
    deps["confirmacao_state"].obter = MagicMock(return_value=estado)
    deps["confirmacao_chain"].interpretar = AsyncMock(
        return_value=ConfirmacaoResposta(tipo="sim")
    )
    deps["alterar"].confirmar = AsyncMock(return_value="Lançamento alterado com sucesso!")

    await pipeline.processar("5511999999999", "pode ser")

    deps["confirmacao_chain"].interpretar.assert_called_once_with("pode ser", "sim_nao")
    deps["alterar"].confirmar.assert_called_once_with("5511999999999", True)
    deps["formatador"].formatar.assert_called_once()
    _, tipo = deps["formatador"].formatar.call_args[0]
    assert tipo == "confirmacao"


@pytest.mark.asyncio
async def test_intencao_marcar_pago_inicia_e_formata_confirmacao():
    pipeline, deps = _make_pipeline()
    deps["classificador"].classificar = AsyncMock(
        return_value=IntencaoResult(intencao="MARCAR_PAGO", confianca="alta")
    )
    deps["marcar_pago"].iniciar = AsyncMock(return_value="card de confirmação")

    await pipeline.processar("5511999999999", "paguei o jogo do batman")

    deps["marcar_pago"].iniciar.assert_called_once_with("paguei o jogo do batman", "5511999999999")
    deps["formatador"].formatar.assert_called_once_with("card de confirmação", "confirmacao")


@pytest.mark.asyncio
async def test_estado_marcar_pago_sim_confirma_com_true():
    estado = EstadoConfirmacao(acao="MARCAR_PAGO", transacao_id=42)
    pipeline, deps = _make_pipeline()
    deps["confirmacao_state"].obter = MagicMock(return_value=estado)
    deps["confirmacao_chain"].interpretar = AsyncMock(
        return_value=ConfirmacaoResposta(tipo="sim")
    )
    deps["marcar_pago"].confirmar = AsyncMock(return_value="Lançamento marcado como pago!")

    await pipeline.processar("5511999999999", "sim")

    deps["confirmacao_chain"].interpretar.assert_called_once_with("sim", "sim_nao")
    deps["marcar_pago"].confirmar.assert_called_once_with("5511999999999", True)
    deps["formatador"].formatar.assert_called_once()
    _, tipo = deps["formatador"].formatar.call_args[0]
    assert tipo == "confirmacao"


@pytest.mark.asyncio
async def test_estado_marcar_pago_nao_confirma_com_false():
    estado = EstadoConfirmacao(acao="MARCAR_PAGO", transacao_id=42)
    pipeline, deps = _make_pipeline()
    deps["confirmacao_state"].obter = MagicMock(return_value=estado)
    deps["confirmacao_chain"].interpretar = AsyncMock(
        return_value=ConfirmacaoResposta(tipo="nao")
    )
    deps["marcar_pago"].confirmar = AsyncMock(return_value="Operação cancelada.")

    await pipeline.processar("5511999999999", "não")

    deps["marcar_pago"].confirmar.assert_called_once_with("5511999999999", False)


@pytest.mark.asyncio
async def test_estado_excluir_pergunta_grupo_interpreta_escopo_parcela():
    estado = EstadoConfirmacao(acao="EXCLUIR", pergunta_grupo=True)
    pipeline, deps = _make_pipeline()
    deps["confirmacao_state"].obter = MagicMock(return_value=estado)
    deps["confirmacao_chain"].interpretar = AsyncMock(
        return_value=ConfirmacaoResposta(tipo="parcela")
    )
    deps["excluir"].confirmar = AsyncMock(return_value="Parcela excluída com sucesso!")

    await pipeline.processar("5511999999999", "só essa")

    deps["confirmacao_chain"].interpretar.assert_called_once_with("só essa", "escopo_parcela")
    deps["excluir"].confirmar.assert_called_once_with("5511999999999", "parcela")
