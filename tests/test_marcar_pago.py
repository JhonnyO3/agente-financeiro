from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from backend.models.enums import CategoriaEnum, StatusEnum, TipoEnum
from backend.repositories.dtos import TransacaoUpdate
from agent.services.confirmacao_state import ConfirmacaoState, EstadoConfirmacao
from agent.services.marcar_pago import MarcarPagoService


def _make_transacao(parcela_total: int = 1, parcela_numero: int = 1):
    return SimpleNamespace(
        id=42,
        tipo=TipoEnum.GASTO,
        valor=Decimal("150.00"),
        descricao="Jogo do Batman",
        categoria=CategoriaEnum.LAZER,
        data=date(2026, 6, 1),
        parcela_numero=parcela_numero,
        parcela_total=parcela_total,
        grupo_parcela_id=str(uuid4()),
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
def marcar_pago_service(repository, embedder, confirmacao_state):
    return MarcarPagoService(repository, embedder, confirmacao_state)


@pytest.mark.asyncio
async def test_iniciar_encontrado_salva_estado_e_retorna_card(
    marcar_pago_service, repository, confirmacao_state
):
    t = _make_transacao()
    repository.buscar_semantico_com_distancia = AsyncMock(return_value=(t, 0.5))

    resultado = await marcar_pago_service.iniciar("paguei o jogo do batman", "5511999990001")

    repository.buscar_semantico_com_distancia.assert_awaited_once_with([0.1] * 1536, limite=1)
    assert "Encontrei este registro" in resultado
    assert "Jogo do Batman" in resultado
    assert "PAGO" in resultado
    assert "(sim / não)" in resultado
    estado = confirmacao_state.obter("5511999990001")
    assert estado is not None
    assert estado.acao == "MARCAR_PAGO"
    assert estado.transacao_id == 42


@pytest.mark.asyncio
async def test_iniciar_sem_resultado_retorna_nao_encontrado(
    marcar_pago_service, repository, confirmacao_state
):
    repository.buscar_semantico_com_distancia = AsyncMock(return_value=None)

    resultado = await marcar_pago_service.iniciar("paguei o jogo do batman", "5511999990002")

    assert "Não encontrei" in resultado
    assert confirmacao_state.obter("5511999990002") is None


@pytest.mark.asyncio
async def test_iniciar_distancia_alta_retorna_nao_encontrado(
    marcar_pago_service, repository, confirmacao_state
):
    t = _make_transacao()
    repository.buscar_semantico_com_distancia = AsyncMock(return_value=(t, 1.5))

    resultado = await marcar_pago_service.iniciar("paguei o jogo do batman", "5511999990003")

    assert "Não encontrei" in resultado
    assert confirmacao_state.obter("5511999990003") is None


@pytest.mark.asyncio
async def test_confirmar_true_atualiza_status_pago_e_limpa_estado(
    marcar_pago_service, repository, confirmacao_state
):
    estado = EstadoConfirmacao(acao="MARCAR_PAGO", transacao_id=42)
    confirmacao_state.salvar("5511999990004", estado)
    repository.atualizar = AsyncMock(return_value=MagicMock())

    resultado = await marcar_pago_service.confirmar("5511999990004", confirmado=True)

    repository.atualizar.assert_awaited_once_with(42, TransacaoUpdate(status=StatusEnum.PAGO))
    assert "pago" in resultado.lower()
    assert confirmacao_state.obter("5511999990004") is None


@pytest.mark.asyncio
async def test_confirmar_false_cancela_e_limpa_estado(
    marcar_pago_service, repository, confirmacao_state
):
    estado = EstadoConfirmacao(acao="MARCAR_PAGO", transacao_id=42)
    confirmacao_state.salvar("5511999990005", estado)
    repository.atualizar = AsyncMock()

    resultado = await marcar_pago_service.confirmar("5511999990005", confirmado=False)

    repository.atualizar.assert_not_awaited()
    assert "cancelad" in resultado.lower()
    assert confirmacao_state.obter("5511999990005") is None


@pytest.mark.asyncio
async def test_confirmar_sem_estado_pendente(marcar_pago_service, repository):
    repository.atualizar = AsyncMock()

    resultado = await marcar_pago_service.confirmar("5511999990006", confirmado=True)

    repository.atualizar.assert_not_awaited()
    assert "pendente" in resultado.lower()
