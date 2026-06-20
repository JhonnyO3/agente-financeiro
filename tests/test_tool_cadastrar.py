import os

# Defina vars de ambiente antes de qualquer import que carregue Settings
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake-key-for-tests")
os.environ.setdefault("EVOLUTION_API_URL", "http://fake-evolution")
os.environ.setdefault("EVOLUTION_INSTANCE", "fake-instance")
os.environ.setdefault("EVOLUTION_API_KEY", "fake-api-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511999999999")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Jhonatas")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "test@exemplo.com")
os.environ.setdefault("WEBHOOK_APIKEY", "test-apikey")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _relogio_fixo(hoje_date: date):
    """Retorna um Relogio com data fixa para testes."""
    from agent.services.relogio import Relogio

    dt_fixed = datetime(
        hoje_date.year, hoje_date.month, hoje_date.day,
        tzinfo=timezone.utc,
    )
    return Relogio(tz="America/Sao_Paulo", _fixed=dt_fixed)


def _item_pix(descricao="Claude Code", valor=Decimal("472.00"), forma_pagamento="PIX"):
    """ItemCadastro simples sem parcelas com forma PIX explícita."""
    from agent.domain.intencao import ItemCadastro

    return ItemCadastro(
        descricao=descricao,
        valor=valor,
        forma_pagamento=forma_pagamento,
    )


def _item_parcelado(
    descricao="Roupas Zara",
    valor=None,
    parcela_atual=3,
    total_parcelas=5,
    dia_vencimento=10,
    forma_pagamento="CARTAO_CREDITO",
):
    from agent.domain.intencao import ItemCadastro

    return ItemCadastro(
        descricao=descricao,
        valor=valor,
        forma_pagamento=forma_pagamento,
        parcela_atual=parcela_atual,
        total_parcelas=total_parcelas,
        dia_vencimento=dia_vencimento,
    )


def _contexto_basico():
    return {"usuario_id": 1}


# ---------------------------------------------------------------------------
# Importabilidade: ToolCadastrar e _parcelas devem existir
# ---------------------------------------------------------------------------

def test_tool_cadastrar_importavel():
    from agent.tools.cadastrar import ToolCadastrar  # noqa


def test_parcelas_helpers_importaveis():
    from agent.tools._parcelas import (  # noqa
        adicionar_meses,
        status_por_data,
        data_status_por_forma,
        datas_do_grupo,
        valores_das_parcelas,
    )


# ---------------------------------------------------------------------------
# _parcelas: adicionar_meses clampa dia 31
# ---------------------------------------------------------------------------

def test_parcelas_adicionar_meses_preserva_dia():
    from agent.tools._parcelas import adicionar_meses

    assert adicionar_meses(date(2026, 6, 10), 1) == date(2026, 7, 10)
    assert adicionar_meses(date(2026, 6, 10), -1) == date(2026, 5, 10)


def test_parcelas_adicionar_meses_clampa_31():
    from agent.tools._parcelas import adicionar_meses

    assert adicionar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)


def test_parcelas_adicionar_meses_clampa_bissexto():
    from agent.tools._parcelas import adicionar_meses

    assert adicionar_meses(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_parcelas_adicionar_meses_virada_ano():
    from agent.tools._parcelas import adicionar_meses

    assert adicionar_meses(date(2026, 12, 15), 1) == date(2027, 1, 15)


# ---------------------------------------------------------------------------
# _parcelas: valores_das_parcelas — Decimal, resto na última
# ---------------------------------------------------------------------------

def test_parcelas_valores_divisao_exata():
    from agent.tools._parcelas import valores_das_parcelas

    resultado = valores_das_parcelas(Decimal("100.00"), 4)
    assert len(resultado) == 4
    assert all(v == Decimal("25.00") for v in resultado)
    assert sum(resultado) == Decimal("100.00")


def test_parcelas_valores_resto_na_ultima():
    from agent.tools._parcelas import valores_das_parcelas

    resultado = valores_das_parcelas(Decimal("100.00"), 3)
    assert len(resultado) == 3
    assert resultado[0] == Decimal("33.33")
    assert resultado[1] == Decimal("33.33")
    assert resultado[2] == Decimal("33.34")  # absorve centavo extra
    assert sum(resultado) == Decimal("100.00")


def test_parcelas_valores_sem_float():
    """Todos os valores devem ser Decimal, nunca float."""
    from agent.tools._parcelas import valores_das_parcelas

    resultado = valores_das_parcelas(Decimal("99.99"), 7)
    for v in resultado:
        assert isinstance(v, Decimal), f"Esperado Decimal, obtido {type(v)}: {v}"
    assert sum(resultado) == Decimal("99.99")


# ---------------------------------------------------------------------------
# Cenário 1: PIX simples → 1 registro PAGO hoje, aguardando_confirmacao
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pix_simples_gera_registro_pago_hoje():
    from agent.tools.cadastrar import ToolCadastrar

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    # Tool NUNCA persiste — os métodos de escrita NÃO devem ser chamados
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_pix()
    resultado = await tool.executar([item], _contexto_basico())

    assert resultado.status == "aguardando_confirmacao"
    registros = resultado.dados["registros"]
    assert len(registros) == 1

    reg = registros[0]
    assert reg["forma_pagamento"] == "PIX"
    assert reg["status"] == "PAGO"
    assert reg["data"] == date(2026, 6, 11)

    # Nunca persiste
    repository.criar.assert_not_called()
    repository.criar_lote.assert_not_called()


@pytest.mark.asyncio
async def test_pix_simples_responsavel_e_settings_responsavel_padrao():
    from agent.tools.cadastrar import ToolCadastrar

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_pix()

    with patch("agent.tools.cadastrar.settings") as mock_settings:
        mock_settings.RESPONSAVEL_PADRAO = "Responsavel_Teste"
        resultado = await tool.executar([item], _contexto_basico())

    reg = resultado.dados["registros"][0]
    assert reg["responsavel"] == "Responsavel_Teste"
    # Jamais usa o default hardcoded do DTO
    assert reg["responsavel"] != "Jhonatas" or os.environ.get("RESPONSAVEL_PADRAO") == "Jhonatas"


# ---------------------------------------------------------------------------
# Cenário 2: parcelado 3/5, vencimento dia 10 → 3 registros, mesmo grupo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parcelado_gera_apenas_atual_e_futuras():
    """3/5 → registros para parcelas 3, 4, 5 (não as anteriores 1 e 2)."""
    from agent.tools.cadastrar import ToolCadastrar

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_parcelado(valor=Decimal("300.00"), parcela_atual=3, total_parcelas=5, dia_vencimento=10)
    resultado = await tool.executar([item], _contexto_basico())

    assert resultado.status == "aguardando_confirmacao"
    registros = resultado.dados["registros"]
    assert len(registros) == 3  # parcelas 3, 4, 5

    repository.criar.assert_not_called()
    repository.criar_lote.assert_not_called()


@pytest.mark.asyncio
async def test_parcelado_mesmo_grupo_parcela_id():
    from agent.tools.cadastrar import ToolCadastrar

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_parcelado(valor=Decimal("300.00"), parcela_atual=3, total_parcelas=5, dia_vencimento=10)
    resultado = await tool.executar([item], _contexto_basico())

    registros = resultado.dados["registros"]
    grupo_ids = {r["grupo_parcela_id"] for r in registros}
    assert len(grupo_ids) == 1, "Todos os registros do grupo devem ter o mesmo grupo_parcela_id"


@pytest.mark.asyncio
async def test_parcelado_datas_com_dia_preservado():
    """Parcelas 3, 4, 5 com dia_vencimento=10: datas 10/06, 10/07, 10/08."""
    from agent.tools.cadastrar import ToolCadastrar

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_parcelado(valor=Decimal("300.00"), parcela_atual=3, total_parcelas=5, dia_vencimento=10)
    resultado = await tool.executar([item], _contexto_basico())

    registros = resultado.dados["registros"]
    datas = [r["data"] for r in registros]
    assert date(2026, 6, 10) in datas
    assert date(2026, 7, 10) in datas
    assert date(2026, 8, 10) in datas


@pytest.mark.asyncio
async def test_parcelado_parcelas_futuras_no_payload():
    """dados.parcelas_futuras deve conter as parcelas seguintes à atual."""
    from agent.tools.cadastrar import ToolCadastrar

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_parcelado(valor=Decimal("300.00"), parcela_atual=3, total_parcelas=5, dia_vencimento=10)
    resultado = await tool.executar([item], _contexto_basico())

    parcelas_futuras = resultado.dados.get("parcelas_futuras", [])
    assert "Jul/26" in parcelas_futuras
    assert "Ago/26" in parcelas_futuras


# ---------------------------------------------------------------------------
# Cenário 3: status da parcela atual por vencimento — PENDENTE se futura
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parcela_atual_vencimento_futuro_status_pendente():
    """dia_vencimento=10, hoje=11/06 → a parcela atual vence em 10/06 (passado)
    Mas com hoje=2026-06-04 (antes do dia 10) a atual fica PENDENTE."""
    from agent.tools.cadastrar import ToolCadastrar

    # hoje = 4 de junho, vencimento dia 10 (ainda não chegou)
    relogio = _relogio_fixo(date(2026, 6, 4))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_parcelado(
        valor=Decimal("300.00"),
        parcela_atual=3,
        total_parcelas=5,
        dia_vencimento=10,
    )
    resultado = await tool.executar([item], _contexto_basico())

    registros = resultado.dados["registros"]
    # parcela atual é a 3ª → data 10/06
    reg_atual = next(r for r in registros if r["data"] == date(2026, 6, 10))
    assert reg_atual["status"] == "PENDENTE"


@pytest.mark.asyncio
async def test_parcela_atual_vencimento_passado_status_pago():
    """hoje=11/06, vencimento dia 5 → parcela atual (dia 5/06) já passou → PAGO."""
    from agent.tools.cadastrar import ToolCadastrar

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_parcelado(
        valor=Decimal("300.00"),
        parcela_atual=3,
        total_parcelas=5,
        dia_vencimento=5,
    )
    resultado = await tool.executar([item], _contexto_basico())

    registros = resultado.dados["registros"]
    # parcela atual é a 3ª → data 05/06
    reg_atual = next(r for r in registros if r["data"] == date(2026, 6, 5))
    assert reg_atual["status"] == "PAGO"


# ---------------------------------------------------------------------------
# Cenário 4: valor ausente → aguardando_complemento com campos_faltantes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valor_ausente_retorna_aguardando_complemento():
    from agent.tools.cadastrar import ToolCadastrar
    from agent.domain.intencao import ItemCadastro

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = ItemCadastro(descricao="Zara", valor=None)
    resultado = await tool.executar([item], _contexto_basico())

    assert resultado.status == "aguardando_complemento"
    campos = resultado.dados.get("campos_faltantes", [])
    assert "valor" in campos

    repository.criar.assert_not_called()
    repository.criar_lote.assert_not_called()


# ---------------------------------------------------------------------------
# Cenário 5: múltiplos itens → todos os registros no payload
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_multiplos_itens_geram_todos_registros():
    from agent.tools.cadastrar import ToolCadastrar
    from agent.domain.intencao import ItemCadastro

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item1 = ItemCadastro(descricao="Flores Natasha", valor=Decimal("140"), forma_pagamento="PIX")
    item2 = ItemCadastro(descricao="Internet", valor=Decimal("190"), forma_pagamento="PIX")
    resultado = await tool.executar([item1, item2], _contexto_basico())

    assert resultado.status == "aguardando_confirmacao"
    registros = resultado.dados["registros"]
    assert len(registros) == 2

    valores = {r["valor"] for r in registros}
    assert Decimal("140") in valores
    assert Decimal("190") in valores

    repository.criar.assert_not_called()
    repository.criar_lote.assert_not_called()


@pytest.mark.asyncio
async def test_multiplos_itens_valores_sao_decimal():
    from agent.tools.cadastrar import ToolCadastrar
    from agent.domain.intencao import ItemCadastro

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item1 = ItemCadastro(descricao="Flores Natasha", valor=Decimal("140"), forma_pagamento="PIX")
    item2 = ItemCadastro(descricao="Internet", valor=Decimal("190"), forma_pagamento="PIX")
    resultado = await tool.executar([item1, item2], _contexto_basico())

    for reg in resultado.dados["registros"]:
        assert isinstance(reg["valor"], Decimal), (
            f"Valor deve ser Decimal, obtido {type(reg['valor'])}: {reg['valor']}"
        )


# ---------------------------------------------------------------------------
# Cenário 6: DINHEIRO → PIX + detalhes "dinheiro"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dinheiro_mapeado_para_pix_com_detalhes():
    from agent.tools.cadastrar import ToolCadastrar
    from agent.domain.intencao import ItemCadastro

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = ItemCadastro(
        descricao="Padaria",
        valor=Decimal("15.00"),
        forma_pagamento="DINHEIRO",
    )
    resultado = await tool.executar([item], _contexto_basico())

    reg = resultado.dados["registros"][0]
    assert reg["forma_pagamento"] == "PIX"
    assert reg.get("detalhes") == "dinheiro"


# ---------------------------------------------------------------------------
# Cenário 7: responsavel sempre RESPONSAVEL_PADRAO de Settings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_responsavel_usa_settings_nunca_default_dto():
    from agent.tools.cadastrar import ToolCadastrar

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_pix()

    with patch("agent.tools.cadastrar.settings") as mock_settings:
        mock_settings.RESPONSAVEL_PADRAO = "TesteResponsavel"
        resultado = await tool.executar([item], _contexto_basico())

    reg = resultado.dados["registros"][0]
    assert reg["responsavel"] == "TesteResponsavel"


# ---------------------------------------------------------------------------
# Cenário 8: matemática de parcelas em Decimal — 100/3 → 33.33, 33.33, 33.34
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_matematica_parcelas_decimal_sem_float():
    from agent.tools.cadastrar import ToolCadastrar
    from agent.domain.intencao import ItemCadastro

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = ItemCadastro(
        descricao="Compra parcelada",
        valor=Decimal("100"),
        forma_pagamento="CARTAO_CREDITO",
        parcela_atual=1,
        total_parcelas=3,
        dia_vencimento=15,
    )
    resultado = await tool.executar([item], _contexto_basico())

    registros = resultado.dados["registros"]
    assert len(registros) == 3

    valores = sorted(r["valor"] for r in registros)
    assert valores[0] == Decimal("33.33")
    assert valores[1] == Decimal("33.33")
    assert valores[2] == Decimal("33.34")
    assert sum(r["valor"] for r in registros) == Decimal("100.00")


# ---------------------------------------------------------------------------
# Cenário 9: forma_pagamento ausente → inferida como PIX
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forma_pagamento_ausente_inferida_pix():
    """Sem forma e sem pistas de parcelamento/vencimento → pede forma_pagamento."""
    from agent.tools.cadastrar import ToolCadastrar
    from agent.domain.intencao import ItemCadastro

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = ItemCadastro(descricao="Uber", valor=Decimal("25.00"), forma_pagamento=None)
    resultado = await tool.executar([item], _contexto_basico())

    assert resultado.status == "aguardando_complemento"
    assert "forma_pagamento" in resultado.dados["campos_faltantes"]


# ---------------------------------------------------------------------------
# Cenário 10: ToolCadastrar.executar retorna ResultadoTool válido
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retorno_e_resultado_tool():
    from agent.tools.cadastrar import ToolCadastrar
    from agent.domain.resultado import ResultadoTool

    relogio = _relogio_fixo(date(2026, 6, 11))
    repository = MagicMock()
    repository.criar = AsyncMock()
    repository.criar_lote = AsyncMock()

    tool = ToolCadastrar(relogio=relogio, repository=repository)
    item = _item_pix()
    resultado = await tool.executar([item], _contexto_basico())

    assert isinstance(resultado, ResultadoTool)
    assert resultado.acao == "cadastrar"
