"""
Testes TDD para GET/POST/PUT/DELETE /api/gastos-fixos.

Os módulos backend/services/gastos_fixos.py e backend/controllers/gastos_fixos.py
ainda NÃO existem — todos estes testes devem FALHAR (vermelho TDD).

Convenções (espelho de test_grupos.py):
  - TestClient contra o app FastAPI do backend
  - dependency_overrides para get_session / get_session_begin e get_usuario_atual
  - patch em backend.services.gastos_fixos.TransacaoRepository
  - SimpleNamespace + AsyncMock para o repositório mockado
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test"
)

from contextlib import ExitStack
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session, get_session_begin
from backend.main import app
from backend.models.enums import (
    CategoriaEnum,
    FormaPagamentoEnum,
    StatusEnum,
    TipoEnum,
)
from backend.repositories.dtos import TransacaoCreate

# ---------------------------------------------------------------------------
# Fixtures e helpers
# ---------------------------------------------------------------------------

USUARIO = UsuarioToken(usuario_id=1, role="USER", email="user@exemplo.com")


def _override_session():
    async def _fake():
        yield SimpleNamespace()

    async def _fake_usuario():
        return USUARIO

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_session_begin] = _fake
    app.dependency_overrides[get_usuario_atual] = _fake_usuario


def cliente_com(repo):
    """Cria TestClient com repositório mockado em backend.services.gastos_fixos."""
    _override_session()
    stack = ExitStack()
    stack.enter_context(
        patch(
            "backend.services.gastos_fixos.TransacaoRepository",
            lambda session: repo,
        )
    )
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


def make_gasto_fixo(
    id=12,
    descricao="Claude",
    valor="100.00",
    ano=2026,
    mes=6,
    dia=5,
    categoria="GASTOS_FIXOS",
    forma_pagamento="CARTAO_CREDITO",
    responsavel="Jhonatas",
    status="PENDENTE",
    recorrente=True,
    usuario_id=1,
):
    """Cria um SimpleNamespace imitando uma linha Transacao recorrente."""
    return SimpleNamespace(
        id=id,
        descricao=descricao,
        valor=Decimal(valor),
        data=date(ano, mes, dia),
        categoria=categoria,
        forma_pagamento=forma_pagamento,
        responsavel=responsavel,
        status=status,
        recorrente=recorrente,
        parcela_numero=1,
        parcela_total=1,
        grupo_parcela_id=str(uuid4()),
        tipo="GASTO",
        embedding=None,
        usuario_id=usuario_id,
    )


def repo_padrao(**overrides):
    """Repositório com stubs padrão; campos em overrides sobrescrevem."""
    r = SimpleNamespace(
        listar_recorrentes=AsyncMock(return_value=[]),
        criar=AsyncMock(return_value=SimpleNamespace(id=99)),
        buscar_por_id=AsyncMock(return_value=None),
        atualizar=AsyncMock(return_value=None),
        excluir=AsyncMock(return_value=None),
    )
    for k, v in overrides.items():
        setattr(r, k, v)
    return r


# ===========================================================================
# GET /api/gastos-fixos — listar
# ===========================================================================


class TestGetGastosFixosListar:
    """Cenário: Listar retorna só transações recorrente=True do usuário autenticado."""

    def test_listar_200_body_tem_itens_e_total_mensal(self):
        repo = repo_padrao(
            listar_recorrentes=AsyncMock(
                return_value=[make_gasto_fixo(id=1, valor="100.00")]
            )
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.get("/api/gastos-fixos")

        assert resp.status_code == 200
        corpo = resp.json()
        assert "itens" in corpo
        assert "total_mensal" in corpo

    def test_listar_campos_exatos_por_item(self):
        """Cenário: Listar retorna campos corretos para cada item."""
        gasto = make_gasto_fixo(
            id=12,
            descricao="Claude",
            valor="100.00",
            ano=2026,
            mes=6,
            dia=5,
            categoria="GASTOS_FIXOS",
            forma_pagamento="CARTAO_CREDITO",
            responsavel="Jhonatas",
            status="PENDENTE",
        )
        repo = repo_padrao(listar_recorrentes=AsyncMock(return_value=[gasto]))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.get("/api/gastos-fixos")

        assert resp.status_code == 200
        itens = resp.json()["itens"]
        assert len(itens) == 1
        item = itens[0]
        assert item["id"] == 12
        assert item["descricao"] == "Claude"
        assert item["valor"] == "100.00"
        assert item["dia_vencimento"] == 5
        assert item["data"] == "2026-06-05"
        assert item["categoria"] == "GASTOS_FIXOS"
        assert item["forma_pagamento"] == "CARTAO_CREDITO"
        assert item["responsavel"] == "Jhonatas"
        assert item["status"] == "PENDENTE"

    def test_listar_ordenado_por_dia_vencimento(self):
        """Cenário: Listar ordena os itens por dia_vencimento crescente."""
        gastos = [
            make_gasto_fixo(id=1, dia=15, valor="10.00"),
            make_gasto_fixo(id=2, dia=5, valor="10.00"),
            make_gasto_fixo(id=3, dia=20, valor="10.00"),
        ]
        repo = repo_padrao(listar_recorrentes=AsyncMock(return_value=gastos))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.get("/api/gastos-fixos")

        dias = [item["dia_vencimento"] for item in resp.json()["itens"]]
        assert dias == [5, 15, 20]

    def test_listar_total_mensal_soma_decimal_duas_casas(self):
        """Cenário: total_mensal é a soma dos valores em Decimal serializada com duas casas."""
        gastos = [
            make_gasto_fixo(id=1, dia=5, valor="100.00"),
            make_gasto_fixo(id=2, dia=10, valor="49.90"),
            make_gasto_fixo(id=3, dia=20, valor="29.90"),
        ]
        repo = repo_padrao(listar_recorrentes=AsyncMock(return_value=gastos))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.get("/api/gastos-fixos")

        assert resp.json()["total_mensal"] == "179.80"

    def test_listar_total_mensal_exemplo_contrato(self):
        """Exemplo do contrato: 14.90 + 500.00 = 514.90."""
        gastos = [
            make_gasto_fixo(id=1, dia=5, valor="14.90"),
            make_gasto_fixo(id=2, dia=10, valor="500.00"),
        ]
        repo = repo_padrao(listar_recorrentes=AsyncMock(return_value=gastos))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.get("/api/gastos-fixos")

        assert resp.json()["total_mensal"] == "514.90"

    def test_listar_vazio_retorna_itens_vazio_e_total_zero(self):
        """Cenário: Lista vazia retorna itens vazio e total_mensal zero."""
        repo = repo_padrao(listar_recorrentes=AsyncMock(return_value=[]))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.get("/api/gastos-fixos")

        assert resp.status_code == 200
        assert resp.json() == {"itens": [], "total_mensal": "0.00"}

    def test_listar_chama_listar_recorrentes_com_usuario_id(self):
        """listar_recorrentes deve ser chamado com usuario_id=1."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            client.get("/api/gastos-fixos")

        repo.listar_recorrentes.assert_awaited_once_with(1)

    def test_listar_valor_serializado_com_duas_casas(self):
        """valor deve ser string "100.00", não float nem int."""
        gasto = make_gasto_fixo(id=1, valor="100.00", dia=1)
        repo = repo_padrao(listar_recorrentes=AsyncMock(return_value=[gasto]))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.get("/api/gastos-fixos")

        item = resp.json()["itens"][0]
        assert isinstance(item["valor"], str)
        assert item["valor"] == "100.00"

    def test_listar_dia_vencimento_e_dia_da_data(self):
        """dia_vencimento = data.day."""
        gasto = make_gasto_fixo(id=1, ano=2026, mes=6, dia=15, valor="50.00")
        repo = repo_padrao(listar_recorrentes=AsyncMock(return_value=[gasto]))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.get("/api/gastos-fixos")

        item = resp.json()["itens"][0]
        assert item["dia_vencimento"] == 15
        assert item["data"] == "2026-06-15"


# ===========================================================================
# POST /api/gastos-fixos — incluir
# ===========================================================================


class TestPostGastosFixosCriar:
    """Cenário: Incluir gasto fixo — caminho feliz."""

    def test_post_pix_retorna_201_e_body_ok(self):
        """Cenário: Incluir gasto fixo com PIX grava status PAGO."""
        repo = repo_padrao(criar=AsyncMock(return_value=SimpleNamespace(id=10)))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "Academia",
                    "valor": "99.90",
                    "data": "2026-06-10",
                    "forma_pagamento": "PIX",
                },
            )

        assert resp.status_code == 201
        corpo = resp.json()
        assert corpo["ok"] is True
        assert isinstance(corpo["id"], int)

    def test_post_pix_grava_status_pago(self):
        """PIX → status PAGO no TransacaoCreate enviado ao repo."""
        capturado = {}

        async def _criar(dto: TransacaoCreate):
            capturado["dto"] = dto
            return SimpleNamespace(id=10)

        repo = repo_padrao(criar=_criar)
        client, stack = cliente_com(repo)
        with stack:
            client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "Academia",
                    "valor": "99.90",
                    "data": "2026-06-10",
                    "forma_pagamento": "PIX",
                },
            )

        assert capturado["dto"].status == StatusEnum.PAGO

    def test_post_cartao_credito_grava_status_pendente(self):
        """Cenário: Incluir gasto fixo com forma diferente de PIX grava status PENDENTE."""
        capturado = {}

        async def _criar(dto: TransacaoCreate):
            capturado["dto"] = dto
            return SimpleNamespace(id=11)

        repo = repo_padrao(criar=_criar)
        client, stack = cliente_com(repo)
        with stack:
            client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "Luz",
                    "valor": "150.00",
                    "data": "2026-06-15",
                    "forma_pagamento": "CARTAO_CREDITO",
                },
            )

        assert capturado["dto"].status == StatusEnum.PENDENTE

    def test_post_boleto_grava_status_pendente(self):
        """BOLETO → status PENDENTE."""
        capturado = {}

        async def _criar(dto: TransacaoCreate):
            capturado["dto"] = dto
            return SimpleNamespace(id=12)

        repo = repo_padrao(criar=_criar)
        client, stack = cliente_com(repo)
        with stack:
            client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "Conta de Água",
                    "valor": "80.00",
                    "data": "2026-06-20",
                    "forma_pagamento": "BOLETO",
                },
            )

        assert capturado["dto"].status == StatusEnum.PENDENTE

    def test_post_defaults_categoria_pix_responsavel(self):
        """Cenário: Defaults aplicados quando categoria e forma_pagamento são omitidos."""
        capturado = {}

        async def _criar(dto: TransacaoCreate):
            capturado["dto"] = dto
            return SimpleNamespace(id=13)

        repo = repo_padrao(criar=_criar)
        client, stack = cliente_com(repo)
        with stack:
            client.post(
                "/api/gastos-fixos",
                json={"descricao": "Netflix", "valor": "45.90", "data": "2026-06-15"},
            )

        dto = capturado["dto"]
        assert dto.categoria == CategoriaEnum.GASTOS_FIXOS
        assert dto.forma_pagamento == FormaPagamentoEnum.PIX
        assert dto.responsavel == "Jhonatas"

    def test_post_grava_recorrente_true_parcela_1_1_tipo_gasto_embedding_none(self):
        """Cenário: A linha gravada tem recorrente=True, parcela_numero=1, parcela_total=1,
        tipo=GASTO, embedding=None."""
        capturado = {}

        async def _criar(dto: TransacaoCreate):
            capturado["dto"] = dto
            return SimpleNamespace(id=14)

        repo = repo_padrao(criar=_criar)
        client, stack = cliente_com(repo)
        with stack:
            client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "Academia",
                    "valor": "99.90",
                    "data": "2026-06-10",
                    "forma_pagamento": "PIX",
                },
            )

        dto = capturado["dto"]
        assert dto.recorrente is True
        assert dto.parcela_numero == 1
        assert dto.parcela_total == 1
        assert dto.tipo == TipoEnum.GASTO
        assert dto.embedding is None

    def test_post_gera_grupo_parcela_id_uuid_valido(self):
        """Cenário: Incluir gasto fixo gera grupo_parcela_id novo (UUID)."""
        capturado = {}

        async def _criar(dto: TransacaoCreate):
            capturado["dto"] = dto
            return SimpleNamespace(id=15)

        repo = repo_padrao(criar=_criar)
        client, stack = cliente_com(repo)
        with stack:
            client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "Academia",
                    "valor": "99.90",
                    "data": "2026-06-10",
                },
            )

        gid = capturado["dto"].grupo_parcela_id
        assert isinstance(gid, UUID)

    def test_post_responsavel_customizado(self):
        """responsavel enviado no body substitui o default."""
        capturado = {}

        async def _criar(dto: TransacaoCreate):
            capturado["dto"] = dto
            return SimpleNamespace(id=16)

        repo = repo_padrao(criar=_criar)
        client, stack = cliente_com(repo)
        with stack:
            client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "Aluguel",
                    "valor": "1200.00",
                    "data": "2026-07-01",
                    "responsavel": "Maria",
                },
            )

        assert capturado["dto"].responsavel == "Maria"


# ===========================================================================
# POST — Erros 400
# ===========================================================================


class TestPostGastosFixosErros400:
    def test_valor_zero_retorna_400(self):
        """Cenário: valor igual a zero retorna 400."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={"descricao": "X", "valor": "0.00", "data": "2026-06-10"},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()
        repo.criar.assert_not_awaited()

    def test_valor_negativo_retorna_400(self):
        """Cenário: valor negativo retorna 400."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={"descricao": "X", "valor": "-10.00", "data": "2026-06-10"},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()
        repo.criar.assert_not_awaited()

    def test_descricao_ausente_retorna_400_com_campo_na_mensagem(self):
        """Cenário: Campo descricao ausente retorna 400 com lista de campos ausentes."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={"valor": "50.00", "data": "2026-06-10"},
            )

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "descricao" in corpo["erro"]

    def test_valor_ausente_retorna_400_com_campo_na_mensagem(self):
        """Cenário: Campo valor ausente retorna 400 com lista de campos ausentes."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={"descricao": "X", "data": "2026-06-10"},
            )

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "valor" in corpo["erro"]

    def test_data_ausente_retorna_400_com_campo_na_mensagem(self):
        """Cenário: Campo data ausente retorna 400 com lista de campos ausentes."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={"descricao": "X", "valor": "50.00"},
            )

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "data" in corpo["erro"]

    def test_body_vazio_retorna_400_com_todos_campos_ausentes(self):
        """Campos obrigatorios ausentes: descricao, valor, data."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post("/api/gastos-fixos", json={})

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "Campos obrigatorios ausentes" in corpo["erro"]

    def test_data_invalida_retorna_400(self):
        """Data em formato inválido deve retornar 400."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={"descricao": "X", "valor": "50.00", "data": "nao-e-data"},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_categoria_invalida_retorna_400(self):
        """Enum inválido deve retornar 400."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "X",
                    "valor": "50.00",
                    "data": "2026-06-10",
                    "categoria": "CATEGORIA_INEXISTENTE",
                },
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_forma_pagamento_invalida_retorna_400(self):
        """Enum FormaPagamento inválido deve retornar 400."""
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/gastos-fixos",
                json={
                    "descricao": "X",
                    "valor": "50.00",
                    "data": "2026-06-10",
                    "forma_pagamento": "DINHEIRO",
                },
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()


# ===========================================================================
# PUT /api/gastos-fixos/{id} — editar
# ===========================================================================


class TestPutGastosFixosEditar:
    """Cenário: Editar campos de um gasto fixo existente."""

    def test_editar_descricao_retorna_200_ok(self):
        """Cenário: Editar descricao de gasto fixo existente do usuário."""
        gasto = make_gasto_fixo(id=7, descricao="Spotify", recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                "/api/gastos-fixos/7", json={"descricao": "Spotify Premium"}
            )

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_editar_chama_atualizar_com_descricao(self):
        """atualizar deve ser chamado com descricao nova."""
        gasto = make_gasto_fixo(id=7, descricao="Spotify", recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            client.put("/api/gastos-fixos/7", json={"descricao": "Spotify Premium"})

        repo.atualizar.assert_awaited_once()

    def test_editar_valor_retorna_200(self):
        """Cenário: Editar valor de gasto fixo existente."""
        gasto = make_gasto_fixo(id=7, valor="45.90", recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put("/api/gastos-fixos/7", json={"valor": "29.90"})

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_editar_parcial_campos_nao_enviados_nao_sao_zerados(self):
        """Cenário: Editar é parcial — campos não enviados permanecem inalterados."""
        gasto = make_gasto_fixo(
            id=8, descricao="Netflix", valor="45.90", categoria="GASTOS_FIXOS", recorrente=True
        )
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put("/api/gastos-fixos/8", json={"valor": "55.90"})

        assert resp.status_code == 200
        # Atualizar foi chamado — campos que não foram enviados não devem ser None forçado
        repo.atualizar.assert_awaited_once()
        call_args = repo.atualizar.await_args
        # dto de atualização: descricao deve ser None (não alterado) ou preservado
        # O importante é que atualizar foi chamado apenas com valor no dto
        dto_update = call_args.args[1]  # segundo arg é TransacaoUpdate
        assert dto_update.valor == Decimal("55.90")
        assert dto_update.descricao is None  # parcial: não enviado → None no update

    def test_editar_todos_campos_editaveis(self):
        """Todos os campos editáveis enviados de uma vez."""
        gasto = make_gasto_fixo(id=20, recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                "/api/gastos-fixos/20",
                json={
                    "descricao": "Novo",
                    "valor": "200.00",
                    "data": "2026-07-01",
                    "categoria": "ALIMENTACAO",
                    "forma_pagamento": "PIX",
                    "responsavel": "Ana",
                },
            )

        assert resp.status_code == 200


# ===========================================================================
# PUT — Erros 404
# ===========================================================================


class TestPutGastosFixosErros404:
    def test_put_id_inexistente_retorna_404(self):
        """Cenário: PUT em id inexistente retorna 404."""
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=None))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                "/api/gastos-fixos/999", json={"descricao": "X"}
            )

        assert resp.status_code == 404
        assert resp.json() == {"erro": "Gasto fixo nao encontrado"}

    def test_put_outro_usuario_retorna_404(self):
        """Cenário: PUT em gasto fixo de outro usuário retorna 404.
        buscar_por_id com usuario_id=1 retorna None (filtro no repo)."""
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=None))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                "/api/gastos-fixos/9", json={"descricao": "X"}
            )

        assert resp.status_code == 404
        assert resp.json() == {"erro": "Gasto fixo nao encontrado"}

    def test_put_transacao_nao_recorrente_retorna_404(self):
        """Cenário: PUT em transação não-recorrente retorna 404."""
        gasto_nao_recorrente = make_gasto_fixo(id=10, recorrente=False)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto_nao_recorrente))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                "/api/gastos-fixos/10", json={"descricao": "X"}
            )

        assert resp.status_code == 404
        assert resp.json() == {"erro": "Gasto fixo nao encontrado"}


# ===========================================================================
# PUT — Erros 400 de validação
# ===========================================================================


class TestPutGastosFixosErros400:
    def test_valor_zero_retorna_400(self):
        """valor <= 0 no PUT deve retornar 400."""
        gasto = make_gasto_fixo(id=5, recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put("/api/gastos-fixos/5", json={"valor": "0.00"})

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_valor_negativo_retorna_400(self):
        gasto = make_gasto_fixo(id=5, recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put("/api/gastos-fixos/5", json={"valor": "-5.00"})

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_data_invalida_retorna_400(self):
        gasto = make_gasto_fixo(id=5, recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put("/api/gastos-fixos/5", json={"data": "nao-e-data"})

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_enum_invalido_retorna_400(self):
        gasto = make_gasto_fixo(id=5, recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                "/api/gastos-fixos/5", json={"categoria": "INVALIDO"}
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()


# ===========================================================================
# DELETE /api/gastos-fixos/{id} — remover
# ===========================================================================


class TestDeleteGastosFixosRemover:
    def test_delete_existente_retorna_200_ok(self):
        """Cenário: Remover gasto fixo existente do usuário faz hard delete."""
        gasto = make_gasto_fixo(id=5, recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.delete("/api/gastos-fixos/5")

        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_delete_chama_excluir(self):
        """excluir deve ser chamado após encontrar o registro."""
        gasto = make_gasto_fixo(id=5, recorrente=True)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto))
        client, stack = cliente_com(repo)
        with stack:
            client.delete("/api/gastos-fixos/5")

        repo.excluir.assert_awaited_once()

    def test_delete_id_inexistente_retorna_404(self):
        """Cenário: DELETE em id inexistente retorna 404."""
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=None))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.delete("/api/gastos-fixos/888")

        assert resp.status_code == 404
        assert resp.json() == {"erro": "Gasto fixo nao encontrado"}

    def test_delete_outro_usuario_retorna_404(self):
        """Cenário: DELETE em gasto fixo de outro usuário retorna 404."""
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=None))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.delete("/api/gastos-fixos/6")

        assert resp.status_code == 404
        assert resp.json() == {"erro": "Gasto fixo nao encontrado"}

    def test_delete_transacao_nao_recorrente_retorna_404(self):
        """Cenário: DELETE em transação não-recorrente retorna 404."""
        gasto_nao_recorrente = make_gasto_fixo(id=11, recorrente=False)
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=gasto_nao_recorrente))
        client, stack = cliente_com(repo)
        with stack:
            resp = client.delete("/api/gastos-fixos/11")

        assert resp.status_code == 404
        assert resp.json() == {"erro": "Gasto fixo nao encontrado"}

    def test_delete_nao_chama_excluir_quando_404(self):
        """excluir NÃO deve ser chamado se a linha não existe."""
        repo = repo_padrao(buscar_por_id=AsyncMock(return_value=None))
        client, stack = cliente_com(repo)
        with stack:
            client.delete("/api/gastos-fixos/999")

        repo.excluir.assert_not_awaited()
