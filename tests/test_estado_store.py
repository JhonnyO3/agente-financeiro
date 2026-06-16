import os

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("INSTANCE_NAME", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("ADMIN_EMAILS", "admin@exemplo.com")

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from agent.domain.estado import EstadoConversa, Mensagem, OpcaoPendente
from agent.services.estado_store import (
    EstadoStoreMemoria,
    EstadoStoreRedis,
    resumir_pendencia,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AGORA = datetime(2026, 6, 12, 12, 0, 0, tzinfo=timezone.utc)


def _mensagem(papel: str, texto: str, delta_s: int = 0) -> Mensagem:
    return Mensagem(papel=papel, texto=texto, em=AGORA - timedelta(seconds=delta_s))


def _redis_mock(stored: dict | None = None) -> AsyncMock:
    """Cria um cliente Redis mockado que simula armazenamento via dict interno."""
    _store: dict[str, str] = {}

    async def _get(key: str):
        if stored is not None and key not in _store:
            return stored.get(key)
        return _store.get(key)

    async def _setex(key: str, ttl: int, value: str):
        _store[key] = value

    async def _set(key: str, value: str, **kwargs):
        _store[key] = value

    async def _delete(key: str):
        _store.pop(key, None)

    client = AsyncMock()
    client.get = AsyncMock(side_effect=_get)
    client.setex = AsyncMock(side_effect=_setex)
    client.set = AsyncMock(side_effect=_set)
    client.delete = AsyncMock(side_effect=_delete)
    client._store = _store
    return client


# ---------------------------------------------------------------------------
# Fixtures parametrizadas: mesma suíte de comportamento para as duas impls
# ---------------------------------------------------------------------------


@pytest.fixture(params=["memoria", "redis"])
async def store_vazio(request):
    if request.param == "memoria":
        yield EstadoStoreMemoria(max_historico=10, ttl_historico_horas=2)
    else:
        client = _redis_mock()
        yield EstadoStoreRedis(client=client, max_historico=10, ttl_historico_horas=2)


@pytest.fixture(params=["memoria", "redis"])
async def store_com_estado(request):
    """Retorna (store, estado_salvo) já com usuario_id=1 salvo."""
    estado = EstadoConversa(
        usuario_id=1,
        acao_pendente="cadastrar",
        payload_pendente={"x": 1},
        expira_em=AGORA + timedelta(minutes=5),
        historico_expira_em=AGORA + timedelta(hours=24),
    )
    if request.param == "memoria":
        s = EstadoStoreMemoria()
    else:
        client = _redis_mock()
        s = EstadoStoreRedis(client=client)
    await s.salvar(estado)
    yield s, estado


# ---------------------------------------------------------------------------
# Cenário: obter estado para usuario inexistente devolve estado limpo
# ---------------------------------------------------------------------------


async def test_obter_inexistente_retorna_estado_limpo(store_vazio):
    estado = await store_vazio.obter(usuario_id=99, agora=AGORA)

    assert estado is not None
    assert estado.usuario_id == 99
    assert estado.acao_pendente is None
    assert estado.payload_pendente is None
    assert estado.campos_faltantes == []
    assert estado.opcoes is None
    assert estado.historico == []
    assert estado.expira_em is None
    assert estado.historico_expira_em is None


# ---------------------------------------------------------------------------
# Cenário: salvar e recuperar estado ativo
# ---------------------------------------------------------------------------


async def test_salvar_e_recuperar_estado(store_com_estado):
    s, _ = store_com_estado
    recuperado = await s.obter(usuario_id=1, agora=AGORA)

    assert recuperado.acao_pendente == "cadastrar"
    assert recuperado.payload_pendente == {"x": 1}


# ---------------------------------------------------------------------------
# Cenário: pendência expira sem afetar histórico
# ---------------------------------------------------------------------------


async def test_pendencia_expira_sem_afetar_historico(store_vazio):
    msgs = [_mensagem("usuario", f"msg{i}", delta_s=i * 10) for i in range(2)]
    estado = EstadoConversa(
        usuario_id=1,
        acao_pendente="excluir",
        payload_pendente={"y": 2},
        expira_em=AGORA - timedelta(seconds=1),  # JÁ EXPIROU
        historico=msgs,
        historico_expira_em=AGORA + timedelta(hours=24),  # ainda válido
    )
    await store_vazio.salvar(estado)

    agora_apos = AGORA + timedelta(seconds=2)
    recuperado = await store_vazio.obter(usuario_id=1, agora=agora_apos)

    assert recuperado.acao_pendente is None
    assert recuperado.payload_pendente is None
    assert len(recuperado.historico) == 2


# ---------------------------------------------------------------------------
# Cenário: histórico expira sem afetar pendência ativa
# ---------------------------------------------------------------------------


async def test_historico_expira_sem_afetar_pendencia(store_vazio):
    msgs = [_mensagem("assistente", f"resp{i}", delta_s=i * 10) for i in range(2)]
    estado = EstadoConversa(
        usuario_id=1,
        acao_pendente="atualizar",
        payload_pendente={"z": 3},
        expira_em=AGORA + timedelta(minutes=5),  # ainda válido
        historico=msgs,
        historico_expira_em=AGORA - timedelta(seconds=1),  # JÁ EXPIROU
    )
    await store_vazio.salvar(estado)

    agora_apos = AGORA + timedelta(seconds=2)
    recuperado = await store_vazio.obter(usuario_id=1, agora=agora_apos)

    assert recuperado.historico == []
    assert recuperado.acao_pendente == "atualizar"
    assert recuperado.payload_pendente == {"z": 3}


# ---------------------------------------------------------------------------
# Cenário: limpar_pendencia preserva histórico
# ---------------------------------------------------------------------------


async def test_limpar_pendencia_preserva_historico(store_vazio):
    msgs = [_mensagem("usuario", f"m{i}") for i in range(3)]
    estado = EstadoConversa(
        usuario_id=1,
        acao_pendente="cadastrar",
        payload_pendente={"a": 1},
        campos_faltantes=["valor"],
        opcoes=[OpcaoPendente(numero=1, rotulo="Op A", ref={"id": 1})],
        historico=msgs,
        expira_em=AGORA + timedelta(minutes=5),
        historico_expira_em=AGORA + timedelta(hours=24),
    )
    await store_vazio.salvar(estado)
    await store_vazio.limpar_pendencia(usuario_id=1)

    recuperado = await store_vazio.obter(usuario_id=1, agora=AGORA)

    assert recuperado.acao_pendente is None
    assert recuperado.payload_pendente is None
    assert recuperado.opcoes is None
    assert recuperado.campos_faltantes == []
    assert len(recuperado.historico) == 3


# ---------------------------------------------------------------------------
# Cenário: registrar_mensagem respeita o máximo configurável (anel)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "impl,kwargs",
    [
        ("memoria", {"max_historico": 5, "ttl_historico_horas": 2}),
        ("redis", {"max_historico": 5, "ttl_historico_horas": 2}),
    ],
)
async def test_registrar_mensagem_anel_configuravel(impl, kwargs):
    if impl == "memoria":
        store = EstadoStoreMemoria(**kwargs)
    else:
        store = EstadoStoreRedis(client=_redis_mock(), **kwargs)

    # Salva 5 mensagens iniciais
    msgs_iniciais = [
        _mensagem("usuario", f"antiga{i}", delta_s=(5 - i) * 60) for i in range(5)
    ]
    estado = EstadoConversa(
        usuario_id=1,
        historico=msgs_iniciais,
        historico_expira_em=AGORA + timedelta(hours=24),
    )
    await store.salvar(estado)

    # Registra uma nova mensagem — deve deslocar a mais antiga
    nova = _mensagem("usuario", "nova_mensagem")
    await store.registrar_mensagem(usuario_id=1, msg=nova, agora=AGORA)

    recuperado = await store.obter(usuario_id=1, agora=AGORA)

    assert len(recuperado.historico) == 5
    assert recuperado.historico[-1].texto == "nova_mensagem"
    assert all(m.texto != "antiga0" for m in recuperado.historico)


async def test_registrar_mensagem_anel_10_padrao():
    """Com max_historico=10 (padrão), 12 mensagens → apenas 10 permanecem."""
    store = EstadoStoreMemoria()  # usa default=10

    msgs_iniciais = [
        _mensagem("usuario", f"antiga{i}", delta_s=(12 - i) * 60) for i in range(12)
    ]
    estado = EstadoConversa(
        usuario_id=1,
        historico=msgs_iniciais,
        historico_expira_em=AGORA + timedelta(hours=24),
    )
    await store.salvar(estado)

    nova = _mensagem("usuario", "nova")
    await store.registrar_mensagem(usuario_id=1, msg=nova, agora=AGORA)

    recuperado = await store.obter(usuario_id=1, agora=AGORA)
    # 12 + 1 = 13 → trunca para 10
    assert len(recuperado.historico) == 10
    assert recuperado.historico[-1].texto == "nova"


# ---------------------------------------------------------------------------
# Cenário: EstadoStoreRedis serializa JSON com TTL físico de 24h
# ---------------------------------------------------------------------------


async def test_redis_serializa_json_com_ttl_24h():
    client = _redis_mock()
    store = EstadoStoreRedis(client=client)

    estado = EstadoConversa(
        usuario_id=1,
        acao_pendente="cadastrar",
        expira_em=AGORA + timedelta(minutes=5),
        historico_expira_em=AGORA + timedelta(hours=24),
    )
    await store.salvar(estado)

    # Deve ter chamado setex com chave "estado:1" e TTL de 24h (86400s)
    chave_esperada = "estado:1"
    ttl_esperado = 86400

    client.setex.assert_called_once()
    args = client.setex.call_args
    assert args[0][0] == chave_esperada or args.kwargs.get("name") == chave_esperada
    # TTL = 86400
    ttl_passado = args[0][1] if len(args[0]) > 1 else args.kwargs.get("time")
    assert ttl_passado == ttl_esperado

    # JSON salvo deve ser desserializável e reconstruir o estado fielmente
    json_salvo = args[0][2] if len(args[0]) > 2 else args.kwargs.get("value")
    reconstruido = EstadoConversa.model_validate_json(json_salvo)
    assert reconstruido.usuario_id == 1
    assert reconstruido.acao_pendente == "cadastrar"


async def test_redis_obter_reconstroi_estado_do_json():
    estado_original = EstadoConversa(
        usuario_id=7,
        acao_pendente="excluir",
        payload_pendente={"id": 42},
        expira_em=AGORA + timedelta(minutes=5),
        historico_expira_em=AGORA + timedelta(hours=24),
    )
    json_str = estado_original.model_dump_json()

    # Mock retorna o JSON quando get("estado:7") for chamado
    client = _redis_mock(stored={"estado:7": json_str})
    store = EstadoStoreRedis(client=client)

    recuperado = await store.obter(usuario_id=7, agora=AGORA)

    assert recuperado.usuario_id == 7
    assert recuperado.acao_pendente == "excluir"
    assert recuperado.payload_pendente == {"id": 42}


# ---------------------------------------------------------------------------
# Cenário: resumir_pendencia retorna "nenhuma" quando sem pendência
# ---------------------------------------------------------------------------


def test_resumir_pendencia_nenhuma():
    estado = EstadoConversa(usuario_id=1)
    assert resumir_pendencia(estado) == "nenhuma"


# ---------------------------------------------------------------------------
# Esquema: resumir_pendencia cobre os formatos do classificador.md
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "estado,fragmento",
    [
        # cadastrar com payload pronto → aguardando confirmação
        (
            EstadoConversa(
                usuario_id=1,
                acao_pendente="cadastrar",
                payload_pendente={"descricao": "Aluguel", "valor": 1500},
                campos_faltantes=[],
            ),
            "cadastro aguardando confirmação",
        ),
        # cadastrar com campo faltante → aguardando <campo>
        (
            EstadoConversa(
                usuario_id=1,
                acao_pendente="cadastrar",
                campos_faltantes=["valor"],
            ),
            "cadastro aguardando valor",
        ),
        # atualizar com lista de 3 opções → lista de 3 opções exibida
        (
            EstadoConversa(
                usuario_id=1,
                acao_pendente="atualizar",
                opcoes=[
                    OpcaoPendente(numero=1, rotulo="Internet", ref={"id": 1}),
                    OpcaoPendente(numero=2, rotulo="Zara", ref={"id": 2}),
                    OpcaoPendente(numero=3, rotulo="Batman", ref={"id": 3}),
                ],
            ),
            "lista de 3 opções exibida",
        ),
        # excluir com escopo → exclusão aguardando escopo
        (
            EstadoConversa(
                usuario_id=1,
                acao_pendente="excluir",
                opcoes=[
                    OpcaoPendente(
                        numero=1, rotulo="somente este", ref={"escopo": "um"}
                    ),
                    OpcaoPendente(numero=2, rotulo="todos", ref={"escopo": "todos"}),
                ],
            ),
            "exclusão aguardando escopo",
        ),
    ],
)
def test_resumir_pendencia_formatos(estado, fragmento):
    resultado = resumir_pendencia(estado)
    assert fragmento in resultado


# ---------------------------------------------------------------------------
# Cenário: histórico expira após TTL de inatividade (configurável)
# ---------------------------------------------------------------------------


async def test_historico_expira_apos_ttl_inatividade_memoria():
    """Com ttl_historico_horas=2, histórico expirado → retorna vazio."""
    from datetime import timedelta

    store = EstadoStoreMemoria(max_historico=10, ttl_historico_horas=2)
    agora = AGORA

    # Registra mensagem — expira_em = agora + 2h
    msg = _mensagem("usuario", "oi")
    await store.registrar_mensagem(usuario_id=1, msg=msg, agora=agora)

    # Avança o tempo além do TTL (2h + 1s)
    agora_depois = agora + timedelta(hours=2, seconds=1)
    recuperado = await store.obter(usuario_id=1, agora=agora_depois)

    assert recuperado.historico == [], "Histórico deve expirar após TTL de inatividade"


async def test_historico_ainda_valido_dentro_do_ttl_memoria():
    """Dentro do TTL, histórico permanece acessível."""
    from datetime import timedelta

    store = EstadoStoreMemoria(max_historico=10, ttl_historico_horas=2)
    agora = AGORA

    msg = _mensagem("usuario", "oi")
    await store.registrar_mensagem(usuario_id=1, msg=msg, agora=agora)

    # Avança 1h59m — dentro do TTL
    agora_depois = agora + timedelta(hours=1, minutes=59)
    recuperado = await store.obter(usuario_id=1, agora=agora_depois)

    assert len(recuperado.historico) == 1


# ---------------------------------------------------------------------------
# Cenário: isolamento — histórico de um usuário não vaza para outro
# ---------------------------------------------------------------------------


async def test_historico_isolado_por_usuario_id_memoria():
    """Históricos de dois usuários não se misturam em EstadoStoreMemoria."""
    store = EstadoStoreMemoria()

    msg_a = _mensagem("usuario", "mensagem_do_a")
    msg_b = _mensagem("usuario", "mensagem_do_b")

    await store.registrar_mensagem(usuario_id=1, msg=msg_a, agora=AGORA)
    await store.registrar_mensagem(usuario_id=2, msg=msg_b, agora=AGORA)

    estado_a = await store.obter(usuario_id=1, agora=AGORA)
    estado_b = await store.obter(usuario_id=2, agora=AGORA)

    textos_a = [m.texto for m in estado_a.historico]
    textos_b = [m.texto for m in estado_b.historico]

    assert "mensagem_do_a" in textos_a
    assert "mensagem_do_b" not in textos_a
    assert "mensagem_do_b" in textos_b
    assert "mensagem_do_a" not in textos_b
