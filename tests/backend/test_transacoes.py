import os

for var, valor in {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test",
}.items():
    os.environ.setdefault(var, valor)

from contextlib import ExitStack
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

from fastapi.testclient import TestClient

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.models.enums import FormaPagamentoEnum, StatusEnum
from backend.repositories.dtos import TransacaoCreate, TransacaoUpdate
from backend.dependencies import get_session, get_session_begin
from backend.main import app

USUARIO = UsuarioToken(usuario_id=1, role="USER", email="user@exemplo.com")


def _override_session():
    async def _fake():
        yield SimpleNamespace()

    async def _fake_usuario():
        return USUARIO

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_session_begin] = _fake
    app.dependency_overrides[get_usuario_atual] = _fake_usuario


def fake_repo(**overrides):
    repo = SimpleNamespace(
        listar_por_periodo=AsyncMock(return_value=[]),
        criar=AsyncMock(return_value=SimpleNamespace(id=43)),
        buscar_por_id=AsyncMock(return_value=None),
        atualizar=AsyncMock(return_value=None),
        excluir=AsyncMock(return_value=None),
    )
    for nome, valor in overrides.items():
        setattr(repo, nome, valor)
    return repo


def cliente_com(repo):
    _override_session()
    stack = ExitStack()
    stack.enter_context(
        patch(
            "backend.services.transacoes.TransacaoRepository",
            lambda session: repo,
        )
    )
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


def make_transacao(
    id,
    dia=1,
    tipo="GASTO",
    categoria="COMPRAS",
    valor="10.00",
    status="PENDENTE",
    forma_pagamento="PIX",
    responsavel="Jhonatas",
    detalhes=None,
):
    return SimpleNamespace(
        id=id,
        data=date(2026, 6, dia),
        descricao=f"desc-{id}",
        categoria=categoria,
        valor=Decimal(valor),
        parcela_numero=1,
        parcela_total=1,
        tipo=tipo,
        grupo_parcela_id=f"grupo-{id}",
        status=status,
        forma_pagamento=forma_pagamento,
        responsavel=responsavel,
        detalhes=detalhes,
    )


def test_listagem_paginada_25_por_pagina():
    transacoes = [make_transacao(i, dia=(i % 28) + 1) for i in range(1, 39)]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?pagina=1")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert len(corpo["itens"]) == 25
    assert corpo["total"] == 38
    assert corpo["paginas"] == 2
    assert corpo["pagina"] == 1
    assert corpo["por_pagina"] == 25


def test_listagem_segunda_pagina_com_restante():
    transacoes = [make_transacao(i, dia=(i % 28) + 1) for i in range(1, 39)]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?pagina=2")

    corpo = resposta.json()
    assert len(corpo["itens"]) == 13
    assert corpo["pagina"] == 2


def test_listagem_ordenada_por_data_desc_id_desc():
    transacoes = [
        make_transacao(1, dia=5),
        make_transacao(2, dia=9),
        make_transacao(3, dia=9),
        make_transacao(4, dia=1),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    ids = [item["id"] for item in resposta.json()["itens"]]
    assert ids == [3, 2, 1, 4]


def test_filtros_combinados_tipo_e_categoria():
    transacoes = [
        make_transacao(1, tipo="GASTO", categoria="ALIMENTACAO"),
        make_transacao(2, tipo="GASTO", categoria="TRANSPORTE"),
        make_transacao(3, tipo="INVESTIMENTO", categoria="INVESTIMENTO"),
        make_transacao(4, tipo="GASTO", categoria="ALIMENTACAO"),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?tipo=GASTO&categoria=ALIMENTACAO")

    corpo = resposta.json()
    assert corpo["total"] == 2
    assert {item["id"] for item in corpo["itens"]} == {1, 4}


def test_filtro_por_forma_pagamento():
    transacoes = [
        make_transacao(1, forma_pagamento="PIX"),
        make_transacao(2, forma_pagamento="CARTAO_CREDITO"),
        make_transacao(3, forma_pagamento="CARTAO_CREDITO"),
        make_transacao(4, forma_pagamento="BOLETO"),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?forma_pagamento=CARTAO_CREDITO")

    corpo = resposta.json()
    assert corpo["total"] == 2
    assert {item["id"] for item in corpo["itens"]} == {2, 3}


def test_ordenar_por_valor_ascendente():
    transacoes = [
        make_transacao(1, valor="30.00"),
        make_transacao(2, valor="10.00"),
        make_transacao(3, valor="20.00"),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?ordenar=valor&direcao=asc")

    ids = [item["id"] for item in resposta.json()["itens"]]
    assert ids == [2, 3, 1]


def test_ordenar_por_valor_descendente():
    transacoes = [
        make_transacao(1, valor="30.00"),
        make_transacao(2, valor="10.00"),
        make_transacao(3, valor="20.00"),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?ordenar=valor&direcao=desc")

    ids = [item["id"] for item in resposta.json()["itens"]]
    assert ids == [1, 3, 2]


def test_ordenar_coluna_invalida_usa_padrao_data_desc():
    transacoes = [
        make_transacao(1, dia=5),
        make_transacao(2, dia=20),
        make_transacao(3, dia=10),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?ordenar=coluna_inexistente")

    ids = [item["id"] for item in resposta.json()["itens"]]
    assert ids == [2, 3, 1]


def test_post_cria_transacao():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=43)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "descricao": "Mercado",
                "categoria": "ALIMENTACAO",
                "valor": "89.90",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 201
    assert resposta.json() == {"id": 43, "ok": True}

    dto = repo.criar.await_args.args[0]
    assert isinstance(dto, TransacaoCreate)
    assert dto.parcela_numero == 1
    assert dto.parcela_total == 1
    assert isinstance(dto.grupo_parcela_id, UUID)
    assert dto.embedding is None
    assert dto.valor == Decimal("89.90")
    assert dto.data == date(2026, 6, 10)
    assert dto.descricao == "Mercado"


def test_post_descricao_opcional_vira_none():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=7)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].descricao is None


def test_post_sem_valor_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={"data": "2026-06-10", "categoria": "COMPRAS", "tipo": "GASTO"},
        )

    assert resposta.status_code == 400
    assert "erro" in resposta.json()
    repo.criar.assert_not_awaited()


def test_post_tipo_invalido_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "BANANA",
            },
        )

    assert resposta.status_code == 400
    repo.criar.assert_not_awaited()


def test_post_categoria_invalida_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "BANANA",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 400


def test_post_valor_nao_decimal_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "abc",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 400


def test_post_data_invalida_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "10/06/2026",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 400


def test_put_atualiza_apenas_campos_enviados():
    existente = make_transacao(1)
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put("/api/transacoes/1", json={"valor": "75.00"})

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}

    repo.buscar_por_id.assert_awaited_once_with(1, usuario_id=1)
    id_chamado, dados = repo.atualizar.await_args.args
    assert id_chamado == 1
    assert isinstance(dados, TransacaoUpdate)
    assert dados.valor == Decimal("75.00")
    assert dados.tipo is None
    assert dados.descricao is None
    assert dados.categoria is None
    assert dados.data is None


def test_put_id_inexistente_retorna_404():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put("/api/transacoes/99999", json={"valor": "75.00"})

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "Transacao nao encontrada"}
    repo.atualizar.assert_not_awaited()


def test_delete_id_inexistente_retorna_404():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.delete("/api/transacoes/99999")

    assert resposta.status_code == 404
    assert resposta.json() == {"erro": "Transacao nao encontrada"}
    repo.excluir.assert_not_awaited()


def test_delete_remove_e_retorna_ok():
    existente = make_transacao(5)
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.delete("/api/transacoes/5")

    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}
    repo.buscar_por_id.assert_awaited_once_with(5, usuario_id=1)
    repo.excluir.assert_awaited_once_with(5, usuario_id=1)


def test_valores_como_string_decimal_duas_casas():
    transacoes = [
        make_transacao(1, valor="100"),
        make_transacao(2, valor="89.9"),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    valores = {item["id"]: item["valor"] for item in resposta.json()["itens"]}
    for valor in valores.values():
        assert isinstance(valor, str)
    assert valores[1] == "100.00"
    assert valores[2] == "89.90"


def test_serializacao_do_item():
    t = make_transacao(42, dia=9, valor="100.00", categoria="ALIMENTACAO")
    t.descricao = "Coxinha"
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[t]))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    item = resposta.json()["itens"][0]
    assert item == {
        "id": 42,
        "data": "2026-06-09",
        "descricao": "Coxinha",
        "categoria": "ALIMENTACAO",
        "valor": "100.00",
        "parcela_numero": 1,
        "parcela_total": 1,
        "tipo": "GASTO",
        "grupo_parcela_id": "grupo-42",
        "status": "PENDENTE",
        "forma_pagamento": "PIX",
        "responsavel": "Jhonatas",
        "detalhes": "",
    }


def test_serializacao_normaliza_enums_por_valor():
    t = make_transacao(
        7,
        status=StatusEnum.PAGO,
        forma_pagamento=FormaPagamentoEnum.PIX,
        detalhes="Comprado na promocao",
    )
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[t]))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    item = resposta.json()["itens"][0]
    assert item["status"] == "PAGO"
    assert item["forma_pagamento"] == "PIX"
    assert item["detalhes"] == "Comprado na promocao"


def test_filtro_status_combinado_com_tipo():
    transacoes = [
        make_transacao(1, tipo="GASTO", status="PENDENTE"),
        make_transacao(2, tipo="GASTO", status="PAGO"),
        make_transacao(3, tipo="RECEITA", status="PENDENTE"),
        make_transacao(4, tipo="GASTO", status="PENDENTE"),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?status=PENDENTE&tipo=GASTO")

    corpo = resposta.json()
    assert corpo["total"] == 2
    assert {item["id"] for item in corpo["itens"]} == {1, 4}


def test_post_sem_campos_novos_usa_defaults():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=10)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2099-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 201
    dto = repo.criar.await_args.args[0]
    assert dto.status == StatusEnum.PAGO
    assert dto.forma_pagamento == FormaPagamentoEnum.PIX
    assert dto.responsavel == "Jhonatas"
    assert dto.detalhes is None


def test_post_status_invalido_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
                "status": "XYZ",
            },
        )

    assert resposta.status_code == 400
    repo.criar.assert_not_awaited()


def test_post_forma_pagamento_invalida_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
                "forma_pagamento": "DINHEIRO",
            },
        )

    assert resposta.status_code == 400
    repo.criar.assert_not_awaited()


def test_post_sem_forma_pagamento_grava_pix():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=20)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2099-06-10",
                "categoria": "COMPRAS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].forma_pagamento == FormaPagamentoEnum.PIX


def test_post_receita_data_futura_sem_status_fica_pendente():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=16)))
    client, stack = cliente_com(repo)
    amanha = date.today() + timedelta(days=1)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": amanha.isoformat(),
                "categoria": "RECEITA",
                "valor": "5000.00",
                "tipo": "RECEITA",
                "forma_pagamento": "BOLETO",
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].status == StatusEnum.PENDENTE


def test_put_status_invalido_retorna_400():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=make_transacao(1)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put("/api/transacoes/1", json={"status": "XYZ"})

    assert resposta.status_code == 400
    repo.atualizar.assert_not_awaited()
