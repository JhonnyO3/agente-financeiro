import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_API_KEY", "test")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "+5511999990001")

import pytest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from agent.agents.extrator import ExtracaoResult
from agent.agents.extrator_lista import ExtracaoListaResult, ItemLista
from backend.models.enums import CategoriaEnum, StatusEnum
from agent.services.cadastrar import CadastrarService
from agent.services.confirmacao_state import ConfirmacaoState


def _cat(valor):
    return SimpleNamespace(categoria=valor)


def _make_service(usuario_id, extracao_result=None, categorizacao_result=None, criar_lote_result=None):
    extrator = MagicMock()
    extrator.extrair = AsyncMock(return_value=extracao_result)

    categorizador = MagicMock()
    categorizador.categorizar = AsyncMock(return_value=categorizacao_result)

    embedder = MagicMock()
    embedder.gerar_para_transacao = AsyncMock(return_value=[0.1] * 1536)

    repository = MagicMock()
    repository.criar_lote = AsyncMock(return_value=criar_lote_result or [])

    service = CadastrarService(
        repository=repository,
        embedder=embedder,
        extrator=extrator,
        categorizador=categorizador,
        confirmacao_state=ConfirmacaoState(),
        usuario_id=usuario_id,
    )
    return service, repository


def _gasto(**overrides):
    base = dict(
        tipo="GASTO",
        valor_total=Decimal("50.00"),
        valor_por_parcela=None,
        parcela_total=1,
        descricao="mercado",
        data_referencia=date.today(),
        menciona_cartao=False,
    )
    base.update(overrides)
    return ExtracaoResult(**base)


@pytest.mark.asyncio
async def test_gasto_simples_nasce_com_usuario_id_resolvido():
    service, repository = _make_service(
        usuario_id=1,
        extracao_result=_gasto(),
        categorizacao_result=_cat("ALIMENTACAO"),
        criar_lote_result=[MagicMock()],
    )

    await service.executar("Gastei 50 reais no mercado", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].usuario_id == 1


@pytest.mark.asyncio
async def test_responsavel_separado_do_usuario_id():
    service, repository = _make_service(
        usuario_id=1,
        extracao_result=_gasto(responsavel="Mãe"),
        categorizacao_result=_cat("ALIMENTACAO"),
        criar_lote_result=[MagicMock()],
    )

    await service.executar("minha mãe gastou 50 no mercado", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].usuario_id == 1
    assert lote[0].responsavel == "Mãe"


@pytest.mark.asyncio
async def test_receita_nasce_com_usuario_id():
    service, repository = _make_service(
        usuario_id=1,
        extracao_result=_gasto(tipo="RECEITA", valor_total=Decimal("3000.00"), descricao="salário"),
        categorizacao_result=_cat("ALIMENTACAO"),
        criar_lote_result=[MagicMock()],
    )

    await service.executar("Recebi 3000 de salário", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert lote[0].usuario_id == 1
    assert lote[0].categoria == CategoriaEnum.RECEITA


@pytest.mark.asyncio
async def test_parcelas_todas_com_usuario_id():
    service, repository = _make_service(
        usuario_id=1,
        extracao_result=_gasto(
            valor_total=Decimal("300.00"),
            valor_por_parcela=Decimal("100.00"),
            parcela_total=3,
            descricao="fone",
        ),
        categorizacao_result=_cat("COMPRAS"),
        criar_lote_result=[MagicMock()] * 3,
    )

    await service.executar("fone em 3x de 100", "5511999999999")

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 3
    assert all(t.usuario_id == 1 for t in lote)
    grupo = lote[0].grupo_parcela_id
    assert all(t.grupo_parcela_id == grupo for t in lote)


@pytest.mark.asyncio
async def test_lote_todos_com_usuario_id():
    extracao_lista = ExtracaoListaResult(
        itens=[
            ItemLista(
                descricao="LinkedIn",
                valor=Decimal("49.33"),
                parcela_numero=2,
                parcela_total=3,
                data=date.today(),
                tipo="GASTO",
                categoria="GASTOS_FIXOS",
            ),
            ItemLista(
                descricao="mercado",
                valor=Decimal("100.00"),
                data=date.today(),
                tipo="GASTO",
                categoria="ALIMENTACAO",
            ),
        ]
    )
    extrator_lista = MagicMock()
    extrator_lista.extrair = AsyncMock(return_value=extracao_lista)

    service, repository = _make_service(usuario_id=1, criar_lote_result=[MagicMock()] * 4)

    await service.executar_lote("lista de contas", extrator_lista)

    lote = repository.criar_lote.call_args[0][0]
    assert len(lote) == 4
    assert all(t.usuario_id == 1 for t in lote)


@pytest.mark.asyncio
async def test_usuario_id_nao_muda_entre_mensagens():
    service, repository = _make_service(
        usuario_id=1,
        extracao_result=_gasto(),
        categorizacao_result=_cat("ALIMENTACAO"),
        criar_lote_result=[MagicMock()],
    )

    await service.executar("Gastei 50 no mercado", "5511999999999")
    await service.executar("Gastei 50 no mercado", "5511999999999")

    for chamada in repository.criar_lote.call_args_list:
        lote = chamada[0][0]
        assert all(t.usuario_id == 1 for t in lote)


@pytest.mark.asyncio
async def test_lifespan_resolve_usuario_id_por_email():
    from agent.entrypoint.main import resolver_usuario_id

    usuario = SimpleNamespace(id=1, email="jhonatas2004@gmail.com")
    usuario_repo = MagicMock()
    usuario_repo.buscar_por_email = AsyncMock(return_value=usuario)

    resolved = await resolver_usuario_id(usuario_repo, "jhonatas2004@gmail.com")

    usuario_repo.buscar_por_email.assert_awaited_once_with("jhonatas2004@gmail.com")
    assert resolved == 1


@pytest.mark.asyncio
async def test_lifespan_falha_explicita_se_email_nao_existe():
    from agent.entrypoint.main import resolver_usuario_id

    usuario_repo = MagicMock()
    usuario_repo.buscar_por_email = AsyncMock(return_value=None)

    with pytest.raises(RuntimeError, match="jhonatas2004@gmail.com"):
        await resolver_usuario_id(usuario_repo, "jhonatas2004@gmail.com")
