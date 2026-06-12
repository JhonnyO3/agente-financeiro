import os

# Vars obrigatórias ANTES de qualquer import que carregue Settings
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
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
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_transacao(nome: str = "tx") -> MagicMock:
    t = MagicMock()
    t.descricao = nome
    return t


def _make_adapter(candidatos: list[tuple]) -> MagicMock:
    """Adapter mockado que devolve `candidatos` como lista[tuple[Transacao, float]]."""
    adapter = MagicMock()
    adapter.buscar_semantico_multiplos_com_distancia = AsyncMock(return_value=candidatos)
    return adapter


def _make_embedder(embedding: list[float] | None = None) -> MagicMock:
    emb = embedding or [0.1] * 1536
    embedder = MagicMock()
    embedder.embedar = AsyncMock(return_value=emb)
    return embedder


# ---------------------------------------------------------------------------
# Cenário: 1 candidato abaixo do piso com gap suficiente → MATCH
# ---------------------------------------------------------------------------

async def test_match_um_candidato_abaixo_do_piso():
    """1 candidato com distância < PISO; sem 2º candidato → gap infinito ≥ MARGEM → MATCH."""
    from agent.services.rag import BuscaRAG, Faixa  # importação adiada — módulo não existe ainda

    tx_a = _make_transacao("zara")
    adapter = _make_adapter([(tx_a, 0.4)])
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    resultado = await rag.buscar("zara", usuario_id=1)

    assert resultado.faixa == Faixa.MATCH
    assert len(resultado.candidatos) == 1
    assert resultado.candidatos[0][0] is tx_a


async def test_match_dois_candidatos_gap_suficiente():
    """2 candidatos mas gap ≥ MARGEM → o 1º se destaca → MATCH com 1 candidato."""
    from agent.services.rag import BuscaRAG, Faixa

    tx_a, tx_b = _make_transacao("a"), _make_transacao("b")
    # gap = 0.8 - 0.4 = 0.4 ≥ MARGEM padrão (0.15)
    adapter = _make_adapter([(tx_a, 0.4), (tx_b, 0.8)])
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    resultado = await rag.buscar("zara", usuario_id=1)

    assert resultado.faixa == Faixa.MATCH
    assert len(resultado.candidatos) == 1


# ---------------------------------------------------------------------------
# Cenário: 2+ candidatos próximos entre si → AMBIGUO
# ---------------------------------------------------------------------------

async def test_ambiguo_dois_candidatos_gap_insuficiente():
    """2 candidatos; gap = 0.1 < MARGEM (0.15) → AMBIGUO com ambos."""
    from agent.services.rag import BuscaRAG, Faixa

    tx_a, tx_b = _make_transacao("internet a"), _make_transacao("internet b")
    # gap = 0.6 - 0.5 = 0.1 < 0.15
    adapter = _make_adapter([(tx_a, 0.5), (tx_b, 0.6)])
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    resultado = await rag.buscar("internet", usuario_id=1)

    assert resultado.faixa == Faixa.AMBIGUO
    assert len(resultado.candidatos) == 2
    txs = [c[0] for c in resultado.candidatos]
    assert tx_a in txs
    assert tx_b in txs


async def test_ambiguo_respeita_rag_max_opcoes(monkeypatch):
    """AMBIGUO trunca candidatos em RAG_MAX_OPCOES."""
    from agent.services.rag import BuscaRAG, Faixa

    # 8 candidatos todos próximos (gap entre vizinhos = 0.01 < MARGEM=0.15)
    candidatos = [(_make_transacao(f"tx{i}"), 0.5 + i * 0.01) for i in range(8)]
    adapter = _make_adapter(candidatos)
    embedder = _make_embedder()

    monkeypatch.setenv("RAG_MAX_OPCOES", "5")
    # Reimporta settings com o novo valor de env
    import importlib
    import agent.config as cfg_mod
    importlib.reload(cfg_mod)

    with patch("agent.services.rag.settings", cfg_mod.Settings()):
        rag = BuscaRAG(embedder=embedder, adapter=adapter)
        resultado = await rag.buscar("gastos", usuario_id=1)

    assert resultado.faixa == Faixa.AMBIGUO
    assert len(resultado.candidatos) <= 5


# ---------------------------------------------------------------------------
# Cenário: nenhum candidato → PISO
# ---------------------------------------------------------------------------

async def test_piso_lista_vazia():
    """Adapter retorna lista vazia → PISO."""
    from agent.services.rag import BuscaRAG, Faixa

    adapter = _make_adapter([])
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    resultado = await rag.buscar("inexistente", usuario_id=1)

    assert resultado.faixa == Faixa.PISO
    assert resultado.candidatos == []


# ---------------------------------------------------------------------------
# Cenário: todos os candidatos acima do piso → PISO
# ---------------------------------------------------------------------------

async def test_piso_todos_acima_do_piso():
    """Candidato com distância > RAG_PISO (1.0) → PISO."""
    from agent.services.rag import BuscaRAG, Faixa

    tx_a = _make_transacao("flores")
    adapter = _make_adapter([(tx_a, 1.5)])  # 1.5 > piso 1.0
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    resultado = await rag.buscar("flores", usuario_id=1)

    assert resultado.faixa == Faixa.PISO


async def test_piso_distancia_exatamente_no_piso():
    """Distância == RAG_PISO → deve ser PISO (> não inclui igual)."""
    from agent.services.rag import BuscaRAG, Faixa

    tx_a = _make_transacao("borda")
    adapter = _make_adapter([(tx_a, 1.0)])  # igual ao piso padrão
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    resultado = await rag.buscar("borda", usuario_id=1)

    assert resultado.faixa == Faixa.PISO


# ---------------------------------------------------------------------------
# Cenário: texto enviado ao embedder é EXATAMENTE a referência
# ---------------------------------------------------------------------------

async def test_embedder_recebe_referencia_exata():
    """O texto embedado é a referência, não a mensagem crua."""
    from agent.services.rag import BuscaRAG

    tx_a = _make_transacao("zara")
    adapter = _make_adapter([(tx_a, 0.4)])
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    await rag.buscar("zara", usuario_id=1)

    embedder.embedar.assert_awaited_once()
    texto_embedado = embedder.embedar.call_args[0][0]
    assert texto_embedado == "zara", (
        f"Embedder recebeu '{texto_embedado}' em vez de 'zara'"
    )


async def test_embedder_nao_recebe_mensagem_crua():
    """Garante que a mensagem crua com verbos nunca é enviada ao embedder."""
    from agent.services.rag import BuscaRAG

    tx_a = _make_transacao("zara")
    adapter = _make_adapter([(tx_a, 0.4)])
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    await rag.buscar("zara", usuario_id=1)

    texto_embedado = embedder.embedar.call_args[0][0]
    assert texto_embedado != "corrige o valor da zara para 200", (
        "Embedder recebeu a mensagem crua em vez da referência extraída"
    )


# ---------------------------------------------------------------------------
# Cenário: candidatos ordenados por distância crescente
# ---------------------------------------------------------------------------

async def test_candidatos_ordenados_por_distancia_crescente():
    """ResultadoBusca.candidatos deve ter menor distância primeiro."""
    from agent.services.rag import BuscaRAG, Faixa

    tx_a, tx_b = _make_transacao("A"), _make_transacao("B")
    # Adapter entrega na ordem invertida (B=0.8, A=0.3) — BuscaRAG deve ordenar
    adapter = _make_adapter([(tx_b, 0.8), (tx_a, 0.3)])
    embedder = _make_embedder()

    rag = BuscaRAG(embedder=embedder, adapter=adapter)
    resultado = await rag.buscar("ref", usuario_id=1)

    distancias = [d for _, d in resultado.candidatos]
    assert distancias == sorted(distancias), (
        f"Candidatos não estão em ordem crescente: {distancias}"
    )
    assert distancias[0] == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Cenário: limiares lidos de Settings (valores customizados via monkeypatch)
# ---------------------------------------------------------------------------

async def test_limiares_customizados_mudam_classificacao(monkeypatch):
    """Com RAG_PISO=0.3, distância 0.4 fica acima do piso → PISO em vez de MATCH."""
    from agent.services.rag import BuscaRAG, Faixa

    tx_a = _make_transacao("mercado")
    adapter = _make_adapter([(tx_a, 0.4)])
    embedder = _make_embedder()

    # Configura piso abaixo da distância do candidato
    monkeypatch.setenv("RAG_PISO", "0.3")
    monkeypatch.setenv("RAG_MARGEM", "0.15")
    monkeypatch.setenv("RAG_MAX_OPCOES", "5")

    import importlib
    import agent.config as cfg_mod
    importlib.reload(cfg_mod)

    with patch("agent.services.rag.settings", cfg_mod.Settings()):
        rag = BuscaRAG(embedder=embedder, adapter=adapter)
        resultado = await rag.buscar("mercado", usuario_id=1)

    assert resultado.faixa == Faixa.PISO


async def test_margem_customizada_muda_match_para_ambiguo(monkeypatch):
    """Gap 0.1 é ambíguo com MARGEM=0.05, mas MATCH com MARGEM=0.15 padrão.
    Aqui verifica que MARGEM=0.05 torna gap 0.1 suficiente para MATCH."""
    from agent.services.rag import BuscaRAG, Faixa

    tx_a, tx_b = _make_transacao("a"), _make_transacao("b")
    # gap = 0.6 - 0.5 = 0.1; com MARGEM=0.05 → gap ≥ margem → MATCH
    adapter = _make_adapter([(tx_a, 0.5), (tx_b, 0.6)])
    embedder = _make_embedder()

    monkeypatch.setenv("RAG_PISO", "1.0")
    monkeypatch.setenv("RAG_MARGEM", "0.05")
    monkeypatch.setenv("RAG_MAX_OPCOES", "5")

    import importlib
    import agent.config as cfg_mod
    importlib.reload(cfg_mod)

    with patch("agent.services.rag.settings", cfg_mod.Settings()):
        rag = BuscaRAG(embedder=embedder, adapter=adapter)
        resultado = await rag.buscar("ref", usuario_id=1)

    assert resultado.faixa == Faixa.MATCH


# ---------------------------------------------------------------------------
# Cenário: BuscaRAG e Faixa são importáveis do módulo correto
# ---------------------------------------------------------------------------

def test_importar_faixa_e_resultado_busca():
    """Verifica estrutura mínima dos tipos do contrato."""
    from agent.services.rag import Faixa, ResultadoBusca, BuscaRAG  # noqa

    assert Faixa.MATCH == "match"
    assert Faixa.AMBIGUO == "ambiguo"
    assert Faixa.PISO == "piso"
