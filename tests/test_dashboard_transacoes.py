"""Testes da API CRUD de transações do dashboard (T05 + T07 v2).

Cenários de specs/dashboard-flask/scenarios/api-transacoes.feature e
specs/melhorias-dashboard/scenarios/07-api-transacoes.feature.
Sem DB real: repository e SessionFactory mockados no namespace do blueprint.
"""

import os

for var, valor in {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/test",
    "OPENAI_API_KEY": "test",
    "EVOLUTION_API_URL": "http://localhost",
    "EVOLUTION_INSTANCE": "test",
    "EVOLUTION_API_KEY": "test",
    "WHATSAPP_ALLOWED_NUMBER": "5500000000000",
}.items():
    os.environ.setdefault(var, valor)

from contextlib import ExitStack
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID

from app.models.enums import FormaPagamentoEnum, StatusEnum
from app.repositories.dtos import TransacaoCreate, TransacaoUpdate
from dashboard.app import create_app


# --- Infra de mocks -------------------------------------------------------


class _FakeCtx:
    """Context manager async que entrega uma sessão fake."""

    async def __aenter__(self):
        return SimpleNamespace()

    async def __aexit__(self, *exc):
        return False


class FakeSessionFactory:
    """Suporta `async with SessionFactory() as s` e `async with SessionFactory.begin() as s`."""

    def __call__(self):
        return _FakeCtx()

    def begin(self):
        return _FakeCtx()


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
    """Cria o test_client com SessionFactory e TransacaoRepository mockados."""
    stack = ExitStack()
    stack.enter_context(
        patch("dashboard.blueprints.api_transacoes.SessionFactory", FakeSessionFactory())
    )
    stack.enter_context(
        patch(
            "dashboard.blueprints.api_transacoes.TransacaoRepository",
            lambda session: repo,
        )
    )
    return create_app().test_client(), stack


def make_transacao(
    id,
    dia=1,
    tipo="GASTO",
    categoria="OUTROS",
    valor="10.00",
    status="PENDENTE",
    forma_pagamento="OUTRO",
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


# --- Cenário: Listagem paginada com 25 por página -------------------------


def test_listagem_paginada_25_por_pagina():
    transacoes = [make_transacao(i, dia=(i % 28) + 1) for i in range(1, 39)]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?pagina=1")

    assert resposta.status_code == 200
    corpo = resposta.get_json()
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

    corpo = resposta.get_json()
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

    ids = [item["id"] for item in resposta.get_json()["itens"]]
    # data DESC; empate de data (dia 9) desempata por id DESC
    assert ids == [3, 2, 1, 4]


# --- Cenário: Filtros combinados tipo e categoria --------------------------


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

    corpo = resposta.get_json()
    assert corpo["total"] == 2
    assert {item["id"] for item in corpo["itens"]} == {1, 4}
    for item in corpo["itens"]:
        assert item["tipo"] == "GASTO"
        assert item["categoria"] == "ALIMENTACAO"


# --- Cenário: Criar transação manual ---------------------------------------


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
    assert resposta.get_json() == {"id": 43, "ok": True}

    dto = repo.criar.await_args.args[0]
    assert isinstance(dto, TransacaoCreate)
    assert dto.parcela_numero == 1
    assert dto.parcela_total == 1
    assert isinstance(dto.grupo_parcela_id, UUID)
    assert dto.embedding is None
    assert dto.valor == Decimal("89.90")
    assert dto.data == date(2026, 6, 10)
    assert dto.descricao == "Mercado"
    assert dto.tipo == "GASTO"
    assert dto.categoria == "ALIMENTACAO"


def test_post_descricao_opcional_vira_none():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=7)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "OUTROS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].descricao is None


# --- Cenário: POST sem campo obrigatório ------------------------------------


def test_post_sem_valor_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={"data": "2026-06-10", "categoria": "OUTROS", "tipo": "GASTO"},
        )

    assert resposta.status_code == 400
    assert "erro" in resposta.get_json()
    repo.criar.assert_not_awaited()


def test_post_tipo_invalido_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "OUTROS",
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
                "categoria": "OUTROS",
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
                "categoria": "OUTROS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 400


# --- Cenário: PUT atualiza apenas campos enviados ---------------------------


def test_put_atualiza_apenas_campos_enviados():
    existente = make_transacao(1)
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put("/api/transacoes/1", json={"valor": "75.00"})

    assert resposta.status_code == 200
    assert resposta.get_json() == {"ok": True}

    repo.buscar_por_id.assert_awaited_once_with(1)
    id_chamado, dados = repo.atualizar.await_args.args
    assert id_chamado == 1
    assert isinstance(dados, TransacaoUpdate)
    assert dados.valor == Decimal("75.00")
    assert dados.tipo is None
    assert dados.descricao is None
    assert dados.categoria is None
    assert dados.data is None


# --- Cenário: PUT e DELETE com id inexistente -------------------------------


def test_put_id_inexistente_retorna_404():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put("/api/transacoes/99999", json={"valor": "75.00"})

    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "Transacao nao encontrada"}
    repo.atualizar.assert_not_awaited()


def test_delete_id_inexistente_retorna_404():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=None))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.delete("/api/transacoes/99999")

    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "Transacao nao encontrada"}
    repo.excluir.assert_not_awaited()


def test_delete_remove_e_retorna_ok():
    existente = make_transacao(5)
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.delete("/api/transacoes/5")

    assert resposta.status_code == 200
    assert resposta.get_json() == {"ok": True}
    repo.buscar_por_id.assert_awaited_once_with(5)
    repo.excluir.assert_awaited_once_with(5)


# --- Cenário: Valores monetários como string ---------------------------------


def test_valores_como_string_decimal_duas_casas():
    transacoes = [
        make_transacao(1, valor="100"),
        make_transacao(2, valor="89.9"),
        make_transacao(3, valor="12.345"),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    valores = {item["id"]: item["valor"] for item in resposta.get_json()["itens"]}
    for valor in valores.values():
        assert isinstance(valor, str)
    assert valores[1] == "100.00"
    assert valores[2] == "89.90"


# --- Serialização completa do item -------------------------------------------


def test_serializacao_do_item():
    t = make_transacao(42, dia=9, valor="100.00", categoria="ALIMENTACAO")
    t.descricao = "Coxinha"
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[t]))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    item = resposta.get_json()["itens"][0]
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
        "forma_pagamento": "OUTRO",
        "responsavel": "Jhonatas",
        "detalhes": "",
    }


def test_descricao_none_vira_string_vazia():
    t = make_transacao(1)
    t.descricao = None
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[t]))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    assert resposta.get_json()["itens"][0]["descricao"] == ""


# --- T07: Serialização com os novos campos -----------------------------------


def test_serializacao_normaliza_enums_por_valor():
    t = make_transacao(
        7,
        status=StatusEnum.PAGO,
        forma_pagamento=FormaPagamentoEnum.PIX,
        detalhes="Comprado na promoção da Steam",
    )
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[t]))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    item = resposta.get_json()["itens"][0]
    assert item["status"] == "PAGO"
    assert item["forma_pagamento"] == "PIX"
    assert item["responsavel"] == "Jhonatas"
    assert item["detalhes"] == "Comprado na promoção da Steam"


def test_detalhes_none_vira_string_vazia():
    t = make_transacao(1, detalhes=None)
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=[t]))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes")

    assert resposta.get_json()["itens"][0]["detalhes"] == ""


# --- T07: Filtro por status combinado -----------------------------------------


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

    corpo = resposta.get_json()
    assert corpo["total"] == 2
    assert {item["id"] for item in corpo["itens"]} == {1, 4}
    for item in corpo["itens"]:
        assert item["status"] == "PENDENTE"
        assert item["tipo"] == "GASTO"


def test_filtro_status_sozinho():
    transacoes = [
        make_transacao(1, status="PAGO"),
        make_transacao(2, status="PENDENTE"),
    ]
    repo = fake_repo(listar_por_periodo=AsyncMock(return_value=transacoes))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.get("/api/transacoes?status=PAGO")

    corpo = resposta.get_json()
    assert corpo["total"] == 1
    assert corpo["itens"][0]["id"] == 1


# --- T07: POST com defaults e validação ---------------------------------------


def test_post_sem_campos_novos_usa_defaults():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=10)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2099-06-10",
                "categoria": "OUTROS",
                "valor": "50.00",
                "tipo": "GASTO",
            },
        )

    assert resposta.status_code == 201
    dto = repo.criar.await_args.args[0]
    assert dto.status == StatusEnum.PENDENTE
    assert dto.forma_pagamento == FormaPagamentoEnum.OUTRO
    assert dto.responsavel == "Jhonatas"
    assert dto.detalhes is None


def test_post_com_campos_novos_repassa_valores():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=11)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "COMPRAS",
                "valor": "199.90",
                "tipo": "GASTO",
                "status": "PAGO",
                "forma_pagamento": "CARTAO",
                "responsavel": "Maria",
                "detalhes": "Presente de aniversário",
            },
        )

    assert resposta.status_code == 201
    dto = repo.criar.await_args.args[0]
    assert dto.status == StatusEnum.PAGO
    assert dto.forma_pagamento == FormaPagamentoEnum.CARTAO
    assert dto.responsavel == "Maria"
    assert dto.detalhes == "Presente de aniversário"


def test_post_status_invalido_retorna_400():
    repo = fake_repo()
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "OUTROS",
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
                "categoria": "OUTROS",
                "valor": "50.00",
                "tipo": "GASTO",
                "forma_pagamento": "BOLETO",
            },
        )

    assert resposta.status_code == 400
    repo.criar.assert_not_awaited()


# --- T07: POST via PIX nasce pago ----------------------------------------------


def test_post_pix_sem_status_vira_pago():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=12)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2099-06-10",
                "categoria": "OUTROS",
                "valor": "50.00",
                "tipo": "GASTO",
                "forma_pagamento": "PIX",
            },
        )

    assert resposta.status_code == 201
    dto = repo.criar.await_args.args[0]
    assert dto.status == StatusEnum.PAGO
    assert dto.forma_pagamento == FormaPagamentoEnum.PIX


def test_post_pix_com_status_explicito_respeita_o_enviado():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=13)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": "2026-06-10",
                "categoria": "OUTROS",
                "valor": "50.00",
                "tipo": "GASTO",
                "forma_pagamento": "PIX",
                "status": "PENDENTE",
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].status == StatusEnum.PENDENTE


# --- T07: Receita manual sem status — PAGO se data <= hoje ----------------------


def test_post_receita_data_passada_sem_status_vira_pago():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=14)))
    client, stack = cliente_com(repo)
    ontem = date.today() - timedelta(days=1)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": ontem.isoformat(),
                "categoria": "RECEITA",
                "valor": "5000.00",
                "tipo": "RECEITA",
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].status == StatusEnum.PAGO


def test_post_receita_data_hoje_sem_status_vira_pago():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=15)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": date.today().isoformat(),
                "categoria": "RECEITA",
                "valor": "5000.00",
                "tipo": "RECEITA",
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].status == StatusEnum.PAGO


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
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].status == StatusEnum.PENDENTE


def test_post_receita_com_status_explicito_respeita_o_enviado():
    repo = fake_repo(criar=AsyncMock(return_value=SimpleNamespace(id=17)))
    client, stack = cliente_com(repo)
    ontem = date.today() - timedelta(days=1)
    with stack:
        resposta = client.post(
            "/api/transacoes",
            json={
                "data": ontem.isoformat(),
                "categoria": "RECEITA",
                "valor": "5000.00",
                "tipo": "RECEITA",
                "status": "PENDENTE",
            },
        )

    assert resposta.status_code == 201
    assert repo.criar.await_args.args[0].status == StatusEnum.PENDENTE


# --- T07: PUT parcial dos campos novos -------------------------------------------


def test_put_parcial_so_status():
    existente = make_transacao(1)
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put("/api/transacoes/1", json={"status": "PAGO"})

    assert resposta.status_code == 200
    _, dados = repo.atualizar.await_args.args
    assert dados == TransacaoUpdate(status=StatusEnum.PAGO)


def test_put_aceita_os_quatro_campos_novos():
    existente = make_transacao(1)
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=existente))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put(
            "/api/transacoes/1",
            json={
                "status": "PAGO",
                "forma_pagamento": "CARTAO",
                "responsavel": "Maria",
                "detalhes": "ajustado",
            },
        )

    assert resposta.status_code == 200
    _, dados = repo.atualizar.await_args.args
    assert dados.status == StatusEnum.PAGO
    assert dados.forma_pagamento == FormaPagamentoEnum.CARTAO
    assert dados.responsavel == "Maria"
    assert dados.detalhes == "ajustado"
    assert dados.valor is None
    assert dados.tipo is None


def test_put_status_invalido_retorna_400():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=make_transacao(1)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put("/api/transacoes/1", json={"status": "XYZ"})

    assert resposta.status_code == 400
    repo.atualizar.assert_not_awaited()


def test_put_forma_pagamento_invalida_retorna_400():
    repo = fake_repo(buscar_por_id=AsyncMock(return_value=make_transacao(1)))
    client, stack = cliente_com(repo)
    with stack:
        resposta = client.put("/api/transacoes/1", json={"forma_pagamento": "BOLETO"})

    assert resposta.status_code == 400
    repo.atualizar.assert_not_awaited()
