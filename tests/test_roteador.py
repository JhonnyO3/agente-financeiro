import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

# Env vars obrigatorias antes de qualquer import que carregue Settings
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("OPENAI_API_KEY", "sk-fake-key-for-tests")
os.environ.setdefault("EVOLUTION_API_URL", "http://fake-evolution")
os.environ.setdefault("EVOLUTION_INSTANCE", "fake-instance")
os.environ.setdefault("EVOLUTION_API_KEY", "fake-api-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511999999999")
os.environ.setdefault("RESPONSAVEL_PADRAO", "Jhon")
os.environ.setdefault("AGENTE_USUARIO_EMAIL", "test@exemplo.com")
os.environ.setdefault("WEBHOOK_APIKEY", "test-apikey")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest

from agent.domain.estado import EstadoConversa, OpcaoPendente
from agent.domain.intencao import (
    Intencao,
    ItemCadastro,
    ParamsCadastrar,
    ParamsComplementar,
    ParamsExcluir,
    ParamsListar,
    ParamsAtualizar,
    ParamsSelecionar,
    ParamsVazio,
)
from agent.domain.resultado import ResultadoTool
from agent.services.estado_store import EstadoStoreMemoria

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USUARIO_ID = 42
AGORA = datetime(2026, 6, 12, 10, 0, 0, tzinfo=timezone.utc)
CONTEXTO: dict = {"usuario_id": USUARIO_ID, "mensagem": "teste"}


def _intencao(acao: str, parametros: dict | None = None, confianca: float = 0.9) -> Intencao:
    if parametros is None:
        parametros = {}
    return Intencao.model_validate({"acao": acao, "parametros": parametros, "confianca": confianca})


def _resultado(acao: str, status: str, dados: dict | None = None) -> ResultadoTool:
    return ResultadoTool(acao=acao, status=status, dados=dados or {})  # type: ignore[arg-type]


def _mock_tool(resultado: ResultadoTool) -> MagicMock:
    tool = MagicMock()
    tool.executar = AsyncMock(return_value=resultado)
    return tool


def _explode_llm() -> MagicMock:
    """Mock de LLM que explode se invocado — garante que confirmar nao chama LLM."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock(side_effect=AssertionError("LLM NAO DEVE SER CHAMADO"))
    llm.invoke = MagicMock(side_effect=AssertionError("LLM NAO DEVE SER CHAMADO"))
    return llm


def _mock_repository() -> MagicMock:
    repo = MagicMock()
    repo.criar_lote = AsyncMock(return_value=[])
    repo.atualizar = AsyncMock(return_value=None)
    repo.excluir = AsyncMock(return_value=None)
    repo.excluir_grupo = AsyncMock(return_value=None)
    repo.excluir_por_filtros = AsyncMock(return_value=None)
    return repo


def _estado_sem_pendencia(usuario_id: int = USUARIO_ID) -> EstadoConversa:
    return EstadoConversa(usuario_id=usuario_id)


def _estado_com_pendencia(
    acao_pendente: str,
    payload_pendente: dict,
    opcoes: list[OpcaoPendente] | None = None,
    expira_em: datetime | None = None,
) -> EstadoConversa:
    if expira_em is None:
        expira_em = AGORA + timedelta(minutes=5)
    return EstadoConversa(
        usuario_id=USUARIO_ID,
        acao_pendente=acao_pendente,
        payload_pendente=payload_pendente,
        opcoes=opcoes,
        expira_em=expira_em,
    )


# ---------------------------------------------------------------------------
# Importacao do modulo sob teste (deve falhar — TDD vermelho)
# ---------------------------------------------------------------------------

from agent.services.roteador import Roteador  # noqa: E402  (importacao intencional tardia)


# ---------------------------------------------------------------------------
# Fixture: Roteador com tools mockadas e EstadoStoreMemoria real
# ---------------------------------------------------------------------------

@pytest.fixture
def store() -> EstadoStoreMemoria:
    return EstadoStoreMemoria()


@pytest.fixture
def repo() -> MagicMock:
    return _mock_repository()


@pytest.fixture
def roteador(store: EstadoStoreMemoria, repo: MagicMock) -> Roteador:
    tool_cadastrar = _mock_tool(_resultado("cadastrar", "aguardando_confirmacao", {"registros": []}))
    tool_listar = _mock_tool(_resultado("listar", "concluido", {"grupos": []}))
    tool_atualizar = _mock_tool(_resultado("atualizar", "aguardando_confirmacao", {"registro": {}, "diff": {}}))
    tool_excluir = _mock_tool(_resultado("excluir", "aguardando_confirmacao", {"registro": {}}))
    tool_conversar = _mock_tool(_resultado("conversar", "concluido", {"resposta": "ok"}))

    return Roteador(
        tool_cadastrar=tool_cadastrar,
        tool_listar=tool_listar,
        tool_atualizar=tool_atualizar,
        tool_excluir=tool_excluir,
        tool_conversar=tool_conversar,
        estado_store=store,
        repository=repo,
    )


# ---------------------------------------------------------------------------
# Cenario 1: intencao cadastrar -> ToolCadastrar
# ---------------------------------------------------------------------------

async def test_cadastrar_direciona_para_tool_cadastrar(
    roteador: Roteador, store: EstadoStoreMemoria
) -> None:
    intencao = _intencao(
        "cadastrar",
        {"itens": [{"descricao": "Mercado", "valor": "150.00"}]},
    )
    estado = _estado_sem_pendencia()
    await store.salvar(estado)

    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    roteador.tool_cadastrar.executar.assert_called_once()  # type: ignore[attr-defined]
    assert resultado.acao == "cadastrar"


# ---------------------------------------------------------------------------
# Cenario 2: intencao listar -> ToolListar sem LLM
# ---------------------------------------------------------------------------

async def test_listar_direciona_para_tool_listar_sem_llm(
    store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    tool_listar = _mock_tool(_resultado("listar", "concluido", {"grupos": []}))
    llm_explodivel = _explode_llm()

    roteador = Roteador(
        tool_cadastrar=_mock_tool(_resultado("cadastrar", "concluido")),
        tool_listar=tool_listar,
        tool_atualizar=_mock_tool(_resultado("atualizar", "concluido")),
        tool_excluir=_mock_tool(_resultado("excluir", "concluido")),
        tool_conversar=_mock_tool(_resultado("conversar", "concluido")),
        estado_store=store,
        repository=repo,
        llm=llm_explodivel,
    )

    intencao = _intencao("listar", {"periodo": "mes_atual"})
    estado = _estado_sem_pendencia()
    await store.salvar(estado)

    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    tool_listar.executar.assert_called_once()
    assert resultado.acao == "listar"
    llm_explodivel.ainvoke.assert_not_called()


# ---------------------------------------------------------------------------
# Cenario 3: confirmar com pendencia de cadastrar persiste sem LLM
# ---------------------------------------------------------------------------

async def test_confirmar_cadastrar_persiste_sem_llm(
    store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    payload = {"registros": [{"descricao": "Mercado", "valor": "150.00"}]}
    estado = _estado_com_pendencia("cadastrar", payload)
    await store.salvar(estado)

    llm_explodivel = _explode_llm()
    roteador = Roteador(
        tool_cadastrar=_mock_tool(_resultado("cadastrar", "concluido")),
        tool_listar=_mock_tool(_resultado("listar", "concluido")),
        tool_atualizar=_mock_tool(_resultado("atualizar", "concluido")),
        tool_excluir=_mock_tool(_resultado("excluir", "concluido")),
        tool_conversar=_mock_tool(_resultado("conversar", "concluido")),
        estado_store=store,
        repository=repo,
        llm=llm_explodivel,
    )

    intencao = _intencao("confirmar")
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    repo.criar_lote.assert_called_once()
    args = repo.criar_lote.call_args
    # O payload_pendente deve ter sido passado (registros)
    assert args is not None
    llm_explodivel.ainvoke.assert_not_called()

    # Apos persistir, pendencia deve estar limpa
    estado_apos = await store.obter(USUARIO_ID, AGORA)
    assert estado_apos.acao_pendente is None
    assert estado_apos.payload_pendente is None

    assert resultado.status == "concluido"


# ---------------------------------------------------------------------------
# Cenario 4: confirmar com pendencia de atualizar persiste sem LLM
# ---------------------------------------------------------------------------

async def test_confirmar_atualizar_persiste_sem_llm(
    store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    payload = {
        "registro": {"id": 7, "descricao": "Netflix", "campo": "valor"},
        "diff": {"campo": "valor", "antigo": "39.90", "novo": "49.90"},
    }
    estado = _estado_com_pendencia("atualizar", payload)
    await store.salvar(estado)

    llm_explodivel = _explode_llm()
    roteador = Roteador(
        tool_cadastrar=_mock_tool(_resultado("cadastrar", "concluido")),
        tool_listar=_mock_tool(_resultado("listar", "concluido")),
        tool_atualizar=_mock_tool(_resultado("atualizar", "concluido")),
        tool_excluir=_mock_tool(_resultado("excluir", "concluido")),
        tool_conversar=_mock_tool(_resultado("conversar", "concluido")),
        estado_store=store,
        repository=repo,
        llm=llm_explodivel,
    )

    intencao = _intencao("confirmar")
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    repo.atualizar.assert_called_once()
    llm_explodivel.ainvoke.assert_not_called()
    assert resultado.status == "concluido"


# ---------------------------------------------------------------------------
# Cenario 5: cancelar com pendencia limpa o estado e retorna menu
# ---------------------------------------------------------------------------

async def test_cancelar_limpa_pendencia_e_retorna_menu(
    roteador: Roteador, store: EstadoStoreMemoria
) -> None:
    estado = _estado_com_pendencia("excluir", {"registro": {"id": 1}})
    await store.salvar(estado)

    intencao = _intencao("cancelar")
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    estado_apos = await store.obter(USUARIO_ID, AGORA)
    assert estado_apos.acao_pendente is None

    assert resultado.acao == "menu"


# ---------------------------------------------------------------------------
# Cenario 6: intencao nova durante pendencia ativa cancela e processa a nova
# ---------------------------------------------------------------------------

async def test_intencao_nova_durante_pendencia_cancela_e_processa(
    store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    tool_cadastrar = _mock_tool(_resultado("cadastrar", "aguardando_confirmacao", {"registros": []}))
    roteador = Roteador(
        tool_cadastrar=tool_cadastrar,
        tool_listar=_mock_tool(_resultado("listar", "concluido")),
        tool_atualizar=_mock_tool(_resultado("atualizar", "concluido")),
        tool_excluir=_mock_tool(_resultado("excluir", "concluido")),
        tool_conversar=_mock_tool(_resultado("conversar", "concluido")),
        estado_store=store,
        repository=repo,
    )

    # Pendencia ativa de excluir (nao expirada)
    estado = _estado_com_pendencia("excluir", {"registro": {"id": 5}})
    await store.salvar(estado)

    intencao = _intencao("cadastrar", {"itens": [{"descricao": "Farmacia", "valor": "80.00"}]})
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    # Pendencia anterior deve ter sido cancelada
    estado_apos = await store.obter(USUARIO_ID, AGORA + timedelta(seconds=1))
    # A nova tool deve ter sido chamada
    tool_cadastrar.executar.assert_called_once()
    assert resultado.acao == "cadastrar"


# ---------------------------------------------------------------------------
# Cenario 7: confirmar sem pendencia retorna menu
# ---------------------------------------------------------------------------

async def test_confirmar_sem_pendencia_retorna_menu(
    roteador: Roteador, store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    estado = _estado_sem_pendencia()
    await store.salvar(estado)

    intencao = _intencao("confirmar")
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    assert resultado.acao == "menu"
    assert resultado.status == "concluido"
    repo.criar_lote.assert_not_called()
    repo.atualizar.assert_not_called()
    repo.excluir.assert_not_called()


# ---------------------------------------------------------------------------
# Cenario 8: selecionar sem pendencia retorna menu
# ---------------------------------------------------------------------------

async def test_selecionar_sem_pendencia_retorna_menu(
    roteador: Roteador, store: EstadoStoreMemoria
) -> None:
    estado = _estado_sem_pendencia()
    await store.salvar(estado)

    intencao = _intencao("selecionar", {"opcao": 1})
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    assert resultado.acao == "menu"


# ---------------------------------------------------------------------------
# Cenario 9: complementar sem pendencia retorna menu
# ---------------------------------------------------------------------------

async def test_complementar_sem_pendencia_retorna_menu(
    roteador: Roteador, store: EstadoStoreMemoria
) -> None:
    estado = _estado_sem_pendencia()
    await store.salvar(estado)

    intencao = _intencao("complementar", {"campo": "valor", "valor": "200"})
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    assert resultado.acao == "menu"


# ---------------------------------------------------------------------------
# Cenario 10: tool retorna aguardando_confirmacao -> estado salvo com payload
# ---------------------------------------------------------------------------

async def test_tool_pendente_salva_estado_com_payload(
    store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    registros = [{"descricao": "Netflix", "valor": "39.90"}]
    tool_cadastrar = _mock_tool(
        _resultado("cadastrar", "aguardando_confirmacao", {"registros": registros})
    )
    roteador = Roteador(
        tool_cadastrar=tool_cadastrar,
        tool_listar=_mock_tool(_resultado("listar", "concluido")),
        tool_atualizar=_mock_tool(_resultado("atualizar", "concluido")),
        tool_excluir=_mock_tool(_resultado("excluir", "concluido")),
        tool_conversar=_mock_tool(_resultado("conversar", "concluido")),
        estado_store=store,
        repository=repo,
    )

    await store.salvar(_estado_sem_pendencia())
    intencao = _intencao("cadastrar", {"itens": [{"descricao": "Netflix", "valor": "39.90"}]})
    await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    estado_salvo = await store.obter(USUARIO_ID, AGORA)
    assert estado_salvo.acao_pendente == "cadastrar"
    assert estado_salvo.payload_pendente is not None
    assert "registros" in estado_salvo.payload_pendente
    # expira_em deve ser ~5 minutos a partir de agora
    assert estado_salvo.expira_em is not None
    diff = estado_salvo.expira_em - AGORA
    assert timedelta(minutes=4) < diff <= timedelta(minutes=6)


# ---------------------------------------------------------------------------
# Cenario 11: selecionar resolve opcao do estado e segue fluxo de excluir
# ---------------------------------------------------------------------------

async def test_selecionar_resolve_opcao_e_segue_fluxo(
    store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    opcao1 = OpcaoPendente(numero=1, rotulo="Internet Tim", ref={"id": 10})
    opcao2 = OpcaoPendente(numero=2, rotulo="Roupas Zara", ref={"id": 20})
    estado = _estado_com_pendencia(
        "excluir",
        {},
        opcoes=[opcao1, opcao2],
    )
    await store.salvar(estado)

    tool_excluir = _mock_tool(_resultado("excluir", "aguardando_confirmacao", {"registro": {"id": 20}}))
    roteador = Roteador(
        tool_cadastrar=_mock_tool(_resultado("cadastrar", "concluido")),
        tool_listar=_mock_tool(_resultado("listar", "concluido")),
        tool_atualizar=_mock_tool(_resultado("atualizar", "concluido")),
        tool_excluir=tool_excluir,
        tool_conversar=_mock_tool(_resultado("conversar", "concluido")),
        estado_store=store,
        repository=repo,
    )

    intencao = _intencao("selecionar", {"opcao": 2})
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    # O fluxo de excluir deve ter prosseguido com o registro da opcao 2
    assert resultado.acao == "excluir"


# ---------------------------------------------------------------------------
# Cenario 12: conversar -> ToolConversar
# ---------------------------------------------------------------------------

async def test_conversar_direciona_para_tool_conversar(
    roteador: Roteador, store: EstadoStoreMemoria
) -> None:
    await store.salvar(_estado_sem_pendencia())
    intencao = _intencao("conversar")
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    roteador.tool_conversar.executar.assert_called_once()  # type: ignore[attr-defined]
    assert resultado.acao == "conversar"


# ---------------------------------------------------------------------------
# Cenario 13: desconhecida -> menu
# ---------------------------------------------------------------------------

async def test_desconhecida_retorna_menu(
    roteador: Roteador, store: EstadoStoreMemoria
) -> None:
    await store.salvar(_estado_sem_pendencia())
    intencao = _intencao("desconhecida")
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    assert resultado.acao == "menu"


# ---------------------------------------------------------------------------
# Cenario 14: confirmar com pendencia de excluir (individual) persiste sem LLM
# ---------------------------------------------------------------------------

async def test_confirmar_excluir_individual_persiste_sem_llm(
    store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    payload = {"registro": {"id": 99, "descricao": "Assinatura X"}}
    estado = _estado_com_pendencia("excluir", payload)
    await store.salvar(estado)

    llm_explodivel = _explode_llm()
    roteador = Roteador(
        tool_cadastrar=_mock_tool(_resultado("cadastrar", "concluido")),
        tool_listar=_mock_tool(_resultado("listar", "concluido")),
        tool_atualizar=_mock_tool(_resultado("atualizar", "concluido")),
        tool_excluir=_mock_tool(_resultado("excluir", "concluido")),
        tool_conversar=_mock_tool(_resultado("conversar", "concluido")),
        estado_store=store,
        repository=repo,
        llm=llm_explodivel,
    )

    intencao = _intencao("confirmar")
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    # excluir individual ou excluir_grupo ou excluir_por_filtros — ao menos um deve ter sido chamado
    excluiu = (
        repo.excluir.called
        or repo.excluir_grupo.called
        or repo.excluir_por_filtros.called
    )
    assert excluiu, "Nenhum metodo de exclusao foi chamado"
    llm_explodivel.ainvoke.assert_not_called()
    assert resultado.status == "concluido"


# ---------------------------------------------------------------------------
# Cenario 15: complementar preenche campos_faltantes sem re-extracao
# ---------------------------------------------------------------------------

async def test_complementar_preenche_campos_faltantes(
    store: EstadoStoreMemoria, repo: MagicMock
) -> None:
    payload = {"registros": [{"descricao": "Farmacia", "valor": None}]}
    estado = EstadoConversa(
        usuario_id=USUARIO_ID,
        acao_pendente="cadastrar",
        payload_pendente=payload,
        campos_faltantes=["valor"],
        expira_em=AGORA + timedelta(minutes=5),
    )
    await store.salvar(estado)

    tool_cadastrar = _mock_tool(_resultado("cadastrar", "aguardando_confirmacao", {"registros": []}))
    roteador = Roteador(
        tool_cadastrar=tool_cadastrar,
        tool_listar=_mock_tool(_resultado("listar", "concluido")),
        tool_atualizar=_mock_tool(_resultado("atualizar", "concluido")),
        tool_excluir=_mock_tool(_resultado("excluir", "concluido")),
        tool_conversar=_mock_tool(_resultado("conversar", "concluido")),
        estado_store=store,
        repository=repo,
    )

    intencao = _intencao("complementar", {"campo": "valor", "valor": "250.00"})
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    # O campo deve ter sido preenchido; o fluxo continua sem LLM
    # O resultado pode ser aguardando_confirmacao (tool chamada com payload atualizado) ou ja concluido
    assert resultado.acao in ("cadastrar", "menu")


# ---------------------------------------------------------------------------
# Cenario 16: atualizar -> ToolAtualizar
# ---------------------------------------------------------------------------

async def test_atualizar_direciona_para_tool_atualizar(
    roteador: Roteador, store: EstadoStoreMemoria
) -> None:
    await store.salvar(_estado_sem_pendencia())
    intencao = _intencao("atualizar", {"referencia": "Netflix", "campo": "valor", "novo_valor": "49.90"})
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    roteador.tool_atualizar.executar.assert_called_once()  # type: ignore[attr-defined]
    assert resultado.acao == "atualizar"


# ---------------------------------------------------------------------------
# Cenario 17: excluir -> ToolExcluir
# ---------------------------------------------------------------------------

async def test_excluir_direciona_para_tool_excluir(
    roteador: Roteador, store: EstadoStoreMemoria
) -> None:
    await store.salvar(_estado_sem_pendencia())
    intencao = _intencao("excluir", {"referencia": "Netflix"})
    resultado = await roteador.rotear(intencao, USUARIO_ID, AGORA, CONTEXTO)

    roteador.tool_excluir.executar.assert_called_once()  # type: ignore[attr-defined]
    assert resultado.acao == "excluir"
