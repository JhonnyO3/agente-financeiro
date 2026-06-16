"""
Testes do Worker multi-usuário (TDD — task 04).

Cobre:
- histórico carregado antes de classificar
- registrar_mensagem chamado com (usuario_id, msg, agora)
- dois usuários processados isoladamente com repos distintos
- histórico de um usuário não vaza para o outro
- falha no pipeline envia mensagem amigável sem derrubar o worker
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.domain.estado import EstadoConversa, Mensagem
from agent.domain.resultado import ResultadoTool
from agent.entrypoint.worker import Worker
from agent.services.estado_store import EstadoStoreMemoria


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_intencao(acao: str = "conversar") -> Any:
    from agent.domain.intencao import Intencao, ParamsVazio

    return Intencao(acao=acao, parametros=ParamsVazio(), confianca=0.9)


def _make_resultado(acao: str = "conversar") -> ResultadoTool:
    return ResultadoTool(acao=acao, status="concluido", dados={})


def _make_roteador_mock(resultado: ResultadoTool | None = None) -> AsyncMock:
    roteador = AsyncMock()
    roteador.rotear = AsyncMock(return_value=resultado or _make_resultado())
    return roteador


def _make_worker(
    *,
    estado_store: Any | None = None,
    construir_roteador_fn: Any | None = None,
    repo_factory: Any | None = None,
    classificador: Any | None = None,
    formatador: Any | None = None,
    evolution: Any | None = None,
    debounce: float = 0,
) -> Worker:
    if estado_store is None:
        estado_store = EstadoStoreMemoria()

    if classificador is None:
        classificador = AsyncMock()
        classificador.classificar = AsyncMock(return_value=_make_intencao())

    if formatador is None:
        formatador = MagicMock()
        formatador.formatar = MagicMock(return_value="resposta ok")

    if evolution is None:
        evolution = AsyncMock()
        evolution.enviar_mensagem = AsyncMock()

    roteador_padrao = _make_roteador_mock()
    if construir_roteador_fn is None:
        construir_roteador_fn = MagicMock(return_value=roteador_padrao)

    if repo_factory is None:
        repo_factory = MagicMock(side_effect=lambda uid: MagicMock(name=f"repo_{uid}"))

    return Worker(
        classificador=classificador,
        formatador=formatador,
        evolution_client=evolution,
        estado_store=estado_store,
        construir_roteador=construir_roteador_fn,
        repo_factory=repo_factory,
        debounce_segundos=debounce,
    )


# ---------------------------------------------------------------------------
# Cenário 1 — histórico carregado antes de classificar
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_estado_obtido_antes_de_classificar() -> None:
    """estado_store.obter deve ser chamado ANTES de classificador.classificar."""
    call_order: list[str] = []

    async def _obter(uid: int, agora: datetime) -> EstadoConversa:
        call_order.append("obter")
        return EstadoConversa(usuario_id=uid)

    estado_store = AsyncMock(spec=["obter", "registrar_mensagem"])
    estado_store.obter = AsyncMock(side_effect=_obter)
    estado_store.registrar_mensagem = AsyncMock()

    classificador = AsyncMock()

    async def _classificar(**kwargs: Any) -> Any:
        call_order.append("classificar")
        return _make_intencao()

    classificador.classificar = AsyncMock(side_effect=_classificar)

    worker = _make_worker(estado_store=estado_store, classificador=classificador)
    await worker._processar(usuario_id=1, numero="11999", texto="oi")

    assert call_order[0] == "obter", "obter deve ser chamado antes de classificar"
    assert call_order[1] == "classificar"


@pytest.mark.asyncio
async def test_classificador_recebe_historico_previo() -> None:
    """Quando há 3 mensagens no histórico, classificar deve recebê-las."""
    agora = datetime.now(timezone.utc)
    msgs = [
        Mensagem(papel="usuario", texto="msg1", em=agora),
        Mensagem(papel="assistente", texto="resp1", em=agora),
        Mensagem(papel="usuario", texto="msg2", em=agora),
    ]
    estado_inicial = EstadoConversa(usuario_id=42, historico=msgs)

    estado_store = AsyncMock(spec=["obter", "registrar_mensagem"])
    estado_store.obter = AsyncMock(return_value=estado_inicial)
    estado_store.registrar_mensagem = AsyncMock()

    classificador = AsyncMock()
    classificador.classificar = AsyncMock(return_value=_make_intencao())

    worker = _make_worker(estado_store=estado_store, classificador=classificador)
    await worker._processar(usuario_id=42, numero="11999", texto="nova mensagem")

    classificador.classificar.assert_called_once()
    kwargs = classificador.classificar.call_args.kwargs
    assert len(kwargs["historico"]) == 3
    assert "usuario: msg1" in kwargs["historico"]
    assert "assistente: resp1" in kwargs["historico"]


# ---------------------------------------------------------------------------
# Cenário 2 — registrar_mensagem chamado com (usuario_id, msg, agora)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registrar_mensagem_com_usuario_id_e_instante() -> None:
    """registrar_mensagem deve receber (usuario_id, Mensagem, agora)."""
    estado_store = AsyncMock(spec=["obter", "registrar_mensagem"])
    estado_store.obter = AsyncMock(return_value=EstadoConversa(usuario_id=7))
    estado_store.registrar_mensagem = AsyncMock()

    worker = _make_worker(estado_store=estado_store)
    await worker._processar(usuario_id=7, numero="11999", texto="olá")

    chamadas = estado_store.registrar_mensagem.call_args_list
    # Deve ter sido chamado pelo menos 2 vezes: msg_usuario e msg_assistente
    assert len(chamadas) >= 2

    # Primeira chamada: mensagem do usuário
    uid_arg, msg_arg, _ = chamadas[0].args
    assert uid_arg == 7
    assert isinstance(msg_arg, Mensagem)
    assert msg_arg.papel == "usuario"
    assert msg_arg.texto == "olá"

    # Segunda chamada: mensagem do assistente
    uid_arg2, msg_arg2, _ = chamadas[1].args
    assert uid_arg2 == 7
    assert isinstance(msg_arg2, Mensagem)
    assert msg_arg2.papel == "assistente"


# ---------------------------------------------------------------------------
# Cenário 3 — dois usuários processados isoladamente
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dois_usuarios_repos_distintos() -> None:
    """construir_roteador deve receber repos distintos para cada usuario_id."""
    repos_recebidos: list[Any] = []

    def repo_factory(uid: int) -> MagicMock:
        repo = MagicMock(name=f"repo_uid_{uid}")
        repo._uid = uid
        return repo

    roteador_mock = _make_roteador_mock()

    def construir_roteador(repo: Any) -> Any:
        repos_recebidos.append(repo)
        return roteador_mock

    worker = _make_worker(
        repo_factory=repo_factory,
        construir_roteador_fn=construir_roteador,
    )

    await worker._processar(usuario_id=1, numero="111", texto="msg usuario 1")
    await worker._processar(usuario_id=2, numero="222", texto="msg usuario 2")

    assert len(repos_recebidos) == 2
    assert repos_recebidos[0]._uid == 1
    assert repos_recebidos[1]._uid == 2
    assert repos_recebidos[0] is not repos_recebidos[1], (
        "repos devem ser instâncias distintas"
    )


# ---------------------------------------------------------------------------
# Cenário 4 — histórico de um usuário não vaza para o outro
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_historico_nao_vaza_entre_usuarios() -> None:
    """Cada usuário deve receber apenas o seu próprio histórico."""
    agora = datetime.now(timezone.utc)
    msgs_a = [Mensagem(papel="usuario", texto="somente_A", em=agora)]
    estado_a = EstadoConversa(usuario_id=1, historico=msgs_a)
    estado_b = EstadoConversa(usuario_id=2, historico=[])

    async def obter(uid: int, _agora: datetime) -> EstadoConversa:
        return estado_a if uid == 1 else estado_b

    estado_store = AsyncMock(spec=["obter", "registrar_mensagem"])
    estado_store.obter = AsyncMock(side_effect=obter)
    estado_store.registrar_mensagem = AsyncMock()

    historicos_recebidos: list[list[str]] = []

    async def classificar(**kwargs: Any) -> Any:
        historicos_recebidos.append(list(kwargs.get("historico", [])))
        return _make_intencao()

    classificador = AsyncMock()
    classificador.classificar = AsyncMock(side_effect=classificar)

    worker = _make_worker(estado_store=estado_store, classificador=classificador)

    await worker._processar(usuario_id=1, numero="111", texto="msg")
    await worker._processar(usuario_id=2, numero="222", texto="msg")

    # Historico do usuário A tem "somente_A"
    assert any("somente_A" in h for h in historicos_recebidos[0])
    # Historico do usuário B é vazio
    assert historicos_recebidos[1] == []


# ---------------------------------------------------------------------------
# Cenário 5 — falha no pipeline envia mensagem amigável
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_falha_pipeline_envia_mensagem_amigavel() -> None:
    """Exceção no classificador → mensagem amigável enviada sem derrubar o worker."""
    estado_store = AsyncMock(spec=["obter", "registrar_mensagem"])
    estado_store.obter = AsyncMock(return_value=EstadoConversa(usuario_id=1))
    estado_store.registrar_mensagem = AsyncMock()

    classificador = AsyncMock()
    classificador.classificar = AsyncMock(side_effect=RuntimeError("falha simulada"))

    evolution = AsyncMock()
    evolution.enviar_mensagem = AsyncMock()

    worker = _make_worker(
        estado_store=estado_store,
        classificador=classificador,
        evolution=evolution,
    )

    # Não deve lançar exceção
    await worker._processar(usuario_id=1, numero="11999", texto="oi")

    evolution.enviar_mensagem.assert_called_once()
    args = evolution.enviar_mensagem.call_args.args
    assert args[0] == "11999"
    assert isinstance(args[1], str) and len(args[1]) > 0


# ---------------------------------------------------------------------------
# Cenário extra — receber preserva usuario_id para processamento
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_receber_e_processar_pendentes_preserva_usuario_id() -> None:
    """receber + processar_pendentes deve chamar _processar com o usuario_id correto."""
    processados: list[tuple[int, str, str]] = []

    worker = _make_worker(debounce=0)

    async def _processar_fake(usuario_id: int, numero: str, texto: str) -> None:
        processados.append((usuario_id, numero, texto))

    worker._processar = _processar_fake  # type: ignore[method-assign]

    await worker.receber(usuario_id=99, numero="55999", texto="fragmento")
    await worker.processar_pendentes()

    assert len(processados) == 1
    uid, num, txt = processados[0]
    assert uid == 99
    assert num == "55999"
    assert txt == "fragmento"
