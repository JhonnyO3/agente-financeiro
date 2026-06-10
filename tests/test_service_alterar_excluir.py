from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models.enums import CategoriaEnum, TipoEnum
from app.repositories.dtos import TransacaoUpdate
from app.services.alterar import AlterarService
from app.services.confirmacao_state import ConfirmacaoState, EstadoConfirmacao
from app.services.excluir import ExcluirService


def _make_transacao(parcela_total: int = 1, parcela_numero: int = 1, distancia: float = 0.5):
    grupo_id = uuid4()
    t = SimpleNamespace(
        id=42,
        tipo=TipoEnum.GASTO,
        valor=Decimal("150.00"),
        descricao="Mercado",
        categoria=CategoriaEnum.ALIMENTACAO,
        data=date(2024, 6, 1),
        parcela_numero=parcela_numero,
        parcela_total=parcela_total,
        grupo_parcela_id=str(grupo_id),
    )
    return t, distancia


def _make_extracao(novo_valor=None, nova_descricao=None, nova_categoria=None, nova_data=None):
    return SimpleNamespace(
        novo_valor=novo_valor,
        nova_descricao=nova_descricao,
        nova_categoria=nova_categoria,
        nova_data=nova_data,
    )


@pytest.fixture
def confirmacao_state():
    return ConfirmacaoState()


@pytest.fixture
def repository():
    return MagicMock()


@pytest.fixture
def embedder():
    emb = MagicMock()
    emb.gerar = AsyncMock(return_value=[0.1] * 1536)
    return emb


@pytest.fixture
def extrator_alteracao():
    ext = MagicMock()
    ext.extrair = AsyncMock(return_value=_make_extracao(novo_valor=Decimal("200.00")))
    return ext


@pytest.fixture
def alterar_service(repository, embedder, extrator_alteracao, confirmacao_state):
    return AlterarService(repository, embedder, extrator_alteracao, confirmacao_state)


@pytest.fixture
def excluir_service(repository, embedder, confirmacao_state):
    return ExcluirService(repository, embedder, confirmacao_state)


@pytest.mark.asyncio
async def test_alterar_iniciar_nao_encontrado(alterar_service, repository):
    t, _ = _make_transacao(distancia=1.5)
    repository.buscar_semantico_com_distancia = AsyncMock(return_value=(t, 1.5))
    resultado = await alterar_service.iniciar("alterar mercado", "5511999990001")
    assert "Não encontrei" in resultado


@pytest.mark.asyncio
async def test_alterar_iniciar_encontrado_salva_estado_e_retorna_card(
    alterar_service, repository, confirmacao_state
):
    t, dist = _make_transacao(distancia=0.5)
    repository.buscar_semantico_com_distancia = AsyncMock(return_value=(t, dist))
    resultado = await alterar_service.iniciar("alterar mercado para 200", "5511999990002")
    assert "Encontrei este registro" in resultado
    assert "Mercado" in resultado
    estado = confirmacao_state.obter("5511999990002")
    assert estado is not None
    assert estado.acao == "ALTERAR"
    assert estado.transacao_id == 42


@pytest.mark.asyncio
async def test_alterar_confirmar_true_chama_atualizar(
    alterar_service, repository, confirmacao_state
):
    update = TransacaoUpdate(valor=Decimal("200.00"))
    estado = EstadoConfirmacao(acao="ALTERAR", transacao_id=42, novos_dados=update)
    confirmacao_state.salvar("5511999990003", estado)
    repository.atualizar = AsyncMock(return_value=MagicMock())
    resultado = await alterar_service.confirmar("5511999990003", confirmado=True)
    repository.atualizar.assert_awaited_once_with(42, update)
    assert "sucesso" in resultado.lower()
    assert confirmacao_state.obter("5511999990003") is None


@pytest.mark.asyncio
async def test_alterar_confirmar_false_cancela_e_limpa_estado(
    alterar_service, repository, confirmacao_state
):
    update = TransacaoUpdate(valor=Decimal("200.00"))
    estado = EstadoConfirmacao(acao="ALTERAR", transacao_id=42, novos_dados=update)
    confirmacao_state.salvar("5511999990004", estado)
    repository.atualizar = AsyncMock()
    resultado = await alterar_service.confirmar("5511999990004", confirmado=False)
    repository.atualizar.assert_not_awaited()
    assert "cancelad" in resultado.lower()
    assert confirmacao_state.obter("5511999990004") is None


@pytest.mark.asyncio
async def test_excluir_parcelado_retorna_pergunta_escopo(excluir_service, repository, confirmacao_state):
    t, dist = _make_transacao(parcela_total=3, parcela_numero=2, distancia=0.4)
    repository.buscar_semantico_com_distancia = AsyncMock(return_value=(t, dist))
    resultado = await excluir_service.iniciar("excluir parcela do cartão", "5511999990005")
    assert "Encontrei este registro" in resultado
    estado = confirmacao_state.obter("5511999990005")
    assert estado is not None
    assert estado.pergunta_grupo is True
    assert "parcela" in resultado.lower() or "parcelas" in resultado.lower()


@pytest.mark.asyncio
async def test_excluir_confirmar_grupo_chama_excluir_grupo(
    excluir_service, repository, confirmacao_state
):
    grupo_id = uuid4()
    estado = EstadoConfirmacao(
        acao="EXCLUIR",
        transacao_id=10,
        grupo_parcela_id=grupo_id,
        pergunta_grupo=True,
    )
    confirmacao_state.salvar("5511999990006", estado)
    repository.excluir_grupo = AsyncMock(return_value=3)
    resultado = await excluir_service.confirmar("5511999990006", resposta_tipo="grupo")
    repository.excluir_grupo.assert_awaited_once_with(grupo_id)
    assert "excluíd" in resultado.lower()
    assert confirmacao_state.obter("5511999990006") is None
