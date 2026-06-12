"""
Testes TDD para PUT /api/grupos/{id} e POST /api/grupos.

Os módulos backend/services/grupos.py e backend/controllers/grupos.py ainda NÃO
existem — todos estes testes devem FALHAR (vermelho TDD).

Convenções:
  - TestClient contra o app FastAPI do backend
  - dependency_overrides para get_session_begin e get_usuario_atual
  - patch em backend.services.grupos.TransacaoRepository
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

BODY_PUT_VALIDO = {
    "descricao": "Notebook",
    "valor_parcela": "150.00",
    "proxima_data": "2026-07-10",
    "parcela_atual": 3,
    "parcela_total": 4,
}

BODY_POST_VALIDO = {
    "descricao": "Notebook",
    "valor_parcela": "100.00",
    "parcela_total": 12,
    "parcela_atual": 1,
    "proxima_data": "2026-07-05",
}


def _override_session():
    async def _fake():
        yield SimpleNamespace()

    async def _fake_usuario():
        return USUARIO

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_session_begin] = _fake
    app.dependency_overrides[get_usuario_atual] = _fake_usuario


def cliente_com(repo):
    """Cria TestClient com repositório mockado em backend.services.grupos."""
    _override_session()
    stack = ExitStack()
    stack.enter_context(
        patch("backend.services.grupos.TransacaoRepository", lambda session: repo)
    )
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


def make_linha(
    grupo,
    numero,
    total,
    ano=2026,
    mes=6,
    dia=10,
    valor="100.00",
    descricao="Notebook",
    status="PENDENTE",
    embedding=None,
    categoria="COMPRAS",
    forma_pagamento="CARTAO_CREDITO",
    responsavel="Jhonatas",
):
    """Cria um SimpleNamespace imitando uma linha Transacao com embedding."""
    return SimpleNamespace(
        grupo_parcela_id=grupo,
        parcela_numero=numero,
        parcela_total=total,
        data=date(ano, mes, dia),
        valor=Decimal(valor),
        descricao=descricao,
        status=status,
        embedding=embedding or [0.1, 0.2],
        categoria=categoria,
        forma_pagamento=forma_pagamento,
        responsavel=responsavel,
        usuario_id=1,
        tipo="GASTO",
        recorrente=False,
    )


def repo_padrao(**overrides):
    """Repositório com stubs padrão; campos em overrides sobrescrevem."""
    r = SimpleNamespace(
        buscar_por_grupo_com_embedding=AsyncMock(return_value=[]),
        criar_lote=AsyncMock(return_value=None),
        excluir_por_grupo_e_numeros=AsyncMock(return_value=0),
        listar_recorrentes=AsyncMock(return_value=[]),
    )
    for k, v in overrides.items():
        setattr(r, k, v)
    return r


def grupo_4_parcelas(grupo_id: str):
    """Retorna 4 linhas: 1-2 PAGO, 3-4 PENDENTE."""
    return [
        make_linha(grupo_id, 1, 4, mes=4, dia=10, status="PAGO"),
        make_linha(grupo_id, 2, 4, mes=5, dia=10, status="PAGO"),
        make_linha(grupo_id, 3, 4, mes=6, dia=10, status="PENDENTE"),
        make_linha(grupo_id, 4, 4, mes=7, dia=10, status="PENDENTE"),
    ]


# ===========================================================================
# PUT /api/grupos/{grupo_parcela_id} — cenários de sucesso
# ===========================================================================


class TestPutGruposEditarTitulo:
    """Cenário: Editar título altera descricao de todas as linhas (pagas e pendentes)."""

    def test_editar_titulo_200_e_body_ok(self):
        grupo_id = str(uuid4())
        linhas = grupo_4_parcelas(grupo_id)
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                f"/api/grupos/{grupo_id}",
                json={**BODY_PUT_VALIDO, "descricao": "Novo título"},
            )

        assert resp.status_code == 200
        corpo = resp.json()
        assert corpo["ok"] is True
        assert corpo["grupo_parcela_id"] == grupo_id
        assert corpo["parcela_total"] == 4

    def test_editar_titulo_aplicado_a_todas_linhas(self):
        grupo_id = str(uuid4())
        linhas = grupo_4_parcelas(grupo_id)
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={**BODY_PUT_VALIDO, "descricao": "Novo título"},
            )

        for linha in linhas:
            assert linha.descricao == "Novo título", (
                f"Linha {linha.parcela_numero} deveria ter descricao='Novo título'"
            )


class TestPutGruposEditarValor:
    """Cenário: Editar valor atualiza só as PENDENTE; PAGO permanecem intactas."""

    def test_valor_aplicado_apenas_pendentes(self):
        grupo_id = str(uuid4())
        linhas = grupo_4_parcelas(grupo_id)
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={**BODY_PUT_VALIDO, "valor_parcela": "200.00"},
            )

        # Pagas intactas
        assert linhas[0].valor == Decimal("100.00")
        assert linhas[1].valor == Decimal("100.00")
        # Pendentes atualizadas
        assert linhas[2].valor == Decimal("200.00")
        assert linhas[3].valor == Decimal("200.00")


class TestPutGruposEditarData:
    """Cenário: Editar data move a próxima pendente e recalcula seguintes mês a mês."""

    def test_data_proxima_pendente_e_cadeia(self):
        grupo_id = str(uuid4())
        linhas = [
            make_linha(grupo_id, 1, 4, mes=4, dia=5, status="PAGO"),
            make_linha(grupo_id, 2, 4, mes=5, dia=5, status="PAGO"),
            make_linha(grupo_id, 3, 4, mes=6, dia=5, status="PENDENTE"),
            make_linha(grupo_id, 4, 4, mes=7, dia=5, status="PENDENTE"),
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-08-05",
                    "parcela_atual": 3,
                    "parcela_total": 4,
                },
            )

        # Pagas intactas
        assert linhas[0].data == date(2026, 4, 5)
        assert linhas[1].data == date(2026, 5, 5)
        # Proxima pendente ancorада em 2026-08-05
        assert linhas[2].data == date(2026, 8, 5)
        # Seguinte +1 mês
        assert linhas[3].data == date(2026, 9, 5)

    def test_data_clampa_dia_31_em_fevereiro(self):
        grupo_id = str(uuid4())
        linhas = [
            make_linha(grupo_id, 1, 2, mes=1, dia=31, status="PENDENTE"),
            make_linha(grupo_id, 2, 2, mes=2, dia=28, status="PENDENTE"),
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Assinatura",
                    "valor_parcela": "50.00",
                    "proxima_data": "2026-01-31",
                    "parcela_atual": 1,
                    "parcela_total": 2,
                },
            )

        assert linhas[0].data == date(2026, 1, 31)
        assert linhas[1].data == date(2026, 2, 28)


class TestPutGruposEditarParcelaAtual:
    """Cenário: parcela_atual=N marca 1..N-1 como PAGO e N..total como PENDENTE."""

    def test_status_por_parcela_atual(self):
        grupo_id = str(uuid4())
        linhas = [
            make_linha(grupo_id, i, 5, mes=i + 3, dia=10, status="PENDENTE")
            for i in range(1, 6)
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-06-10",
                    "parcela_atual": 3,
                    "parcela_total": 5,
                },
            )

        assert resp.status_code == 200
        # Parcelas 1 e 2 → PAGO
        assert linhas[0].status == StatusEnum.PAGO
        assert linhas[1].status == StatusEnum.PAGO
        # Parcelas 3, 4, 5 → PENDENTE
        assert linhas[2].status == StatusEnum.PENDENTE
        assert linhas[3].status == StatusEnum.PENDENTE
        assert linhas[4].status == StatusEnum.PENDENTE


class TestPutGruposAumentarTotal:
    """Cenário: Aumentar parcela_total cria linhas novas com mesmo grupo e datas contínuas."""

    def test_aumentar_total_chama_criar_lote(self):
        grupo_id = str(uuid4())
        # 3 parcelas existentes; parcela_atual=2; ultima pendente=3
        linhas = [
            make_linha(grupo_id, 1, 3, mes=5, dia=10, status="PAGO"),
            make_linha(grupo_id, 2, 3, mes=6, dia=10, status="PENDENTE"),
            make_linha(grupo_id, 3, 3, mes=7, dia=10, status="PENDENTE"),
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-07-10",
                    "parcela_atual": 2,
                    "parcela_total": 5,
                },
            )

        assert resp.status_code == 200
        repo.criar_lote.assert_awaited_once()
        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        # Deve criar 2 novas linhas (parcelas 4 e 5)
        assert len(dtos) == 2

    def test_novas_linhas_tem_mesmo_grupo_parcela_id(self):
        grupo_id = str(uuid4())
        embedding_ref = [0.1, 0.2, 0.3]
        linhas = [
            make_linha(grupo_id, 1, 3, mes=5, dia=10, status="PAGO", embedding=embedding_ref),
            make_linha(grupo_id, 2, 3, mes=6, dia=10, status="PENDENTE", embedding=embedding_ref),
            make_linha(grupo_id, 3, 3, mes=7, dia=10, status="PENDENTE", embedding=embedding_ref),
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-07-10",
                    "parcela_atual": 2,
                    "parcela_total": 5,
                },
            )

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        for dto in dtos:
            assert str(dto.grupo_parcela_id) == grupo_id

    def test_novas_linhas_embedding_copiado(self):
        grupo_id = str(uuid4())
        embedding_ref = [0.1, 0.2, 0.3]
        linhas = [
            make_linha(grupo_id, 1, 3, mes=5, dia=10, status="PAGO", embedding=embedding_ref),
            make_linha(grupo_id, 2, 3, mes=6, dia=10, status="PENDENTE", embedding=embedding_ref),
            make_linha(grupo_id, 3, 3, mes=7, dia=10, status="PENDENTE", embedding=embedding_ref),
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-07-10",
                    "parcela_atual": 2,
                    "parcela_total": 5,
                },
            )

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        for dto in dtos:
            assert dto.embedding == embedding_ref

    def test_novas_linhas_datas_continuas(self):
        """Linha 4 = proxima_data + 2 meses (3ª pendente = 2026-07-10, 4ª = 2026-08-10...
        mas como proxima_data ancora a parcela_atual=2, a cadeia é:
        parcela 2 → 2026-07-10, parcela 3 → 2026-08-10, parcela 4 → 2026-09-10, parcela 5 → 2026-10-10"""
        grupo_id = str(uuid4())
        embedding_ref = [0.1, 0.2]
        linhas = [
            make_linha(grupo_id, 1, 3, mes=5, dia=10, status="PAGO", embedding=embedding_ref),
            make_linha(grupo_id, 2, 3, mes=6, dia=10, status="PENDENTE", embedding=embedding_ref),
            make_linha(grupo_id, 3, 3, mes=7, dia=10, status="PENDENTE", embedding=embedding_ref),
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-07-10",
                    "parcela_atual": 2,
                    "parcela_total": 5,
                },
            )

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        # Parcela 4 e 5 (índices 0 e 1 no lote de novas)
        numeros = [dto.parcela_numero for dto in dtos]
        assert 4 in numeros
        assert 5 in numeros

        dto_4 = next(d for d in dtos if d.parcela_numero == 4)
        dto_5 = next(d for d in dtos if d.parcela_numero == 5)
        assert dto_4.data == date(2026, 9, 10)
        assert dto_5.data == date(2026, 10, 10)

    def test_novas_linhas_status_pendente(self):
        grupo_id = str(uuid4())
        linhas = [
            make_linha(grupo_id, 1, 3, mes=5, dia=10, status="PAGO"),
            make_linha(grupo_id, 2, 3, mes=6, dia=10, status="PENDENTE"),
            make_linha(grupo_id, 3, 3, mes=7, dia=10, status="PENDENTE"),
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-07-10",
                    "parcela_atual": 2,
                    "parcela_total": 5,
                },
            )

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        for dto in dtos:
            assert dto.status == StatusEnum.PENDENTE

    def test_parcela_total_atualizado_em_todas_linhas(self):
        grupo_id = str(uuid4())
        linhas = [
            make_linha(grupo_id, 1, 3, mes=5, dia=10, status="PAGO"),
            make_linha(grupo_id, 2, 3, mes=6, dia=10, status="PENDENTE"),
            make_linha(grupo_id, 3, 3, mes=7, dia=10, status="PENDENTE"),
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-07-10",
                    "parcela_atual": 2,
                    "parcela_total": 5,
                },
            )

        for linha in linhas:
            assert linha.parcela_total == 5


class TestPutGruposDiminuirTotal:
    """Cenário: Diminuir parcela_total remove linhas finais e atualiza parcela_total."""

    def test_diminuir_total_chama_excluir_por_grupo_e_numeros(self):
        grupo_id = str(uuid4())
        linhas = [
            make_linha(grupo_id, i, 5, mes=i + 3, dia=10, status="PENDENTE")
            for i in range(1, 6)
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-05-10",
                    "parcela_atual": 2,
                    "parcela_total": 3,
                },
            )

        assert resp.status_code == 200
        repo.excluir_por_grupo_e_numeros.assert_awaited_once()
        args = repo.excluir_por_grupo_e_numeros.await_args.args
        # args[0] = grupo_parcela_id, args[1] = numeros a excluir
        numeros_excluidos = args[1]
        assert sorted(numeros_excluidos) == [4, 5]

    def test_diminuir_total_atualiza_parcela_total_das_restantes(self):
        grupo_id = str(uuid4())
        linhas = [
            make_linha(grupo_id, i, 5, mes=i + 3, dia=10, status="PENDENTE")
            for i in range(1, 6)
        ]
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    "descricao": "Notebook",
                    "valor_parcela": "100.00",
                    "proxima_data": "2026-05-10",
                    "parcela_atual": 2,
                    "parcela_total": 3,
                },
            )

        # As 3 restantes devem ter parcela_total=3
        for linha in linhas[:3]:
            assert linha.parcela_total == 3


# ===========================================================================
# PUT — Erros 400
# ===========================================================================


class TestPutGruposErros400:
    def test_id_malformado_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put("/api/grupos/nao-e-uuid", json=BODY_PUT_VALIDO)

        assert resp.status_code == 400
        assert resp.json() == {"erro": "ID inválido"}
        repo.buscar_por_grupo_com_embedding.assert_not_awaited()

    def test_descricao_ausente_retorna_400(self):
        grupo_id = str(uuid4())
        body = {k: v for k, v in BODY_PUT_VALIDO.items() if k != "descricao"}
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(f"/api/grupos/{grupo_id}", json=body)

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "descricao" in corpo["erro"]

    def test_proxima_data_ausente_retorna_400(self):
        grupo_id = str(uuid4())
        body = {k: v for k, v in BODY_PUT_VALIDO.items() if k != "proxima_data"}
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(f"/api/grupos/{grupo_id}", json=body)

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "proxima_data" in corpo["erro"]

    def test_valor_parcela_ausente_retorna_400(self):
        grupo_id = str(uuid4())
        body = {k: v for k, v in BODY_PUT_VALIDO.items() if k != "valor_parcela"}
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(f"/api/grupos/{grupo_id}", json=body)

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_valor_parcela_zero_retorna_400(self):
        grupo_id = str(uuid4())
        linhas = grupo_4_parcelas(grupo_id)
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                f"/api/grupos/{grupo_id}",
                json={**BODY_PUT_VALIDO, "valor_parcela": "0.00"},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_valor_parcela_negativo_retorna_400(self):
        grupo_id = str(uuid4())
        linhas = grupo_4_parcelas(grupo_id)
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                f"/api/grupos/{grupo_id}",
                json={**BODY_PUT_VALIDO, "valor_parcela": "-10.00"},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_parcela_total_menor_que_parcela_atual_retorna_400(self):
        grupo_id = str(uuid4())
        linhas = grupo_4_parcelas(grupo_id)
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=linhas)
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(
                f"/api/grupos/{grupo_id}",
                json={
                    **BODY_PUT_VALIDO,
                    "parcela_atual": 3,
                    "parcela_total": 2,
                },
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()

    def test_campos_obrigatorios_ausentes_lista_campos_na_mensagem(self):
        grupo_id = str(uuid4())
        # Body completamente vazio
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(f"/api/grupos/{grupo_id}", json={})

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "Campos obrigatorios ausentes" in corpo["erro"]


# ===========================================================================
# PUT — Erro 404
# ===========================================================================


class TestPutGruposErros404:
    def test_grupo_inexistente_retorna_404(self):
        grupo_id = str(uuid4())
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=[])
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(f"/api/grupos/{grupo_id}", json=BODY_PUT_VALIDO)

        assert resp.status_code == 404
        assert resp.json() == {"erro": "Grupo nao encontrado"}

    def test_grupo_outro_usuario_retorna_404(self):
        """Grupo pertencente a outro usuário — buscar_por_grupo_com_embedding retorna []
        porque o filtro usuario_id já filtra na query."""
        grupo_id = str(uuid4())
        repo = repo_padrao(
            buscar_por_grupo_com_embedding=AsyncMock(return_value=[])
        )
        client, stack = cliente_com(repo)
        with stack:
            resp = client.put(f"/api/grupos/{grupo_id}", json=BODY_PUT_VALIDO)

        assert resp.status_code == 404
        assert resp.json() == {"erro": "Grupo nao encontrado"}


# ===========================================================================
# POST /api/grupos — cenários de sucesso
# ===========================================================================


class TestPostGruposCriar:
    """Cenário: Criar 12 parcelas de R$100 gera 12 linhas com o mesmo grupo_parcela_id."""

    def test_post_201_e_body_ok(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post("/api/grupos", json=BODY_POST_VALIDO)

        assert resp.status_code == 201
        corpo = resp.json()
        assert corpo["ok"] is True
        assert "grupo_parcela_id" in corpo
        assert corpo["parcela_total"] == 12

    def test_post_criar_lote_chamado_com_12_dtos(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            client.post("/api/grupos", json=BODY_POST_VALIDO)

        repo.criar_lote.assert_awaited_once()
        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        assert len(dtos) == 12

    def test_post_todas_linhas_mesmo_grupo_parcela_id(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post("/api/grupos", json=BODY_POST_VALIDO)

        grupo_id_retornado = resp.json()["grupo_parcela_id"]
        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        ids_nos_dtos = {str(dto.grupo_parcela_id) for dto in dtos}
        assert len(ids_nos_dtos) == 1
        assert grupo_id_retornado in ids_nos_dtos

    def test_post_valor_100_em_todas_linhas(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            client.post("/api/grupos", json=BODY_POST_VALIDO)

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        for dto in dtos:
            assert dto.valor == Decimal("100.00")

    def test_post_tipo_gasto_recorrente_false_embedding_none(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            client.post("/api/grupos", json=BODY_POST_VALIDO)

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        for dto in dtos:
            assert dto.tipo == TipoEnum.GASTO
            assert dto.recorrente is False
            assert dto.embedding is None


class TestPostGruposParcelaAtual4:
    """Cenário: parcela_atual=4 marca parcelas 1-3 como PAGO e 4-12 como PENDENTE."""

    def test_status_por_parcela_atual(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        body = {**BODY_POST_VALIDO, "parcela_atual": 4}
        with stack:
            client.post("/api/grupos", json=body)

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        pagos = [d for d in dtos if d.status == StatusEnum.PAGO]
        pendentes = [d for d in dtos if d.status == StatusEnum.PENDENTE]

        assert len(pagos) == 3
        assert all(d.parcela_numero < 4 for d in pagos)
        assert len(pendentes) == 9
        assert all(d.parcela_numero >= 4 for d in pendentes)


class TestPostGruposDatas:
    """Cenário: Datas seguem cadeia mensal ancorada na proxima_data."""

    def test_datas_cadeia_mensal(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        body = {
            "descricao": "Notebook",
            "valor_parcela": "100.00",
            "parcela_total": 3,
            "parcela_atual": 1,
            "proxima_data": "2026-07-10",
        }
        with stack:
            client.post("/api/grupos", json=body)

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        dtos_ord = sorted(dtos, key=lambda d: d.parcela_numero)
        assert dtos_ord[0].data == date(2026, 7, 10)
        assert dtos_ord[1].data == date(2026, 8, 10)
        assert dtos_ord[2].data == date(2026, 9, 10)


class TestPostGruposParcelaAtualDefault:
    """Cenário: parcela_atual default é 1 quando omitido."""

    def test_sem_parcela_atual_default_1_todas_pendentes(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        body = {
            "descricao": "Notebook",
            "valor_parcela": "100.00",
            "parcela_total": 3,
            "proxima_data": "2026-07-10",
        }
        with stack:
            resp = client.post("/api/grupos", json=body)

        assert resp.status_code == 201
        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        pagos = [d for d in dtos if d.status == StatusEnum.PAGO]
        assert len(pagos) == 0


class TestPostGruposDefaults:
    """Cenário: Defaults aplicados quando categoria e forma_pagamento são omitidos."""

    def test_defaults_categoria_forma_responsavel(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        body = {
            "descricao": "Notebook",
            "valor_parcela": "100.00",
            "parcela_total": 2,
            "proxima_data": "2026-07-10",
        }
        with stack:
            client.post("/api/grupos", json=body)

        dtos: list[TransacaoCreate] = repo.criar_lote.await_args.args[0]
        for dto in dtos:
            assert dto.categoria == CategoriaEnum.COMPRAS
            assert dto.forma_pagamento == FormaPagamentoEnum.CARTAO_CREDITO
            assert dto.responsavel == "Jhonatas"


# ===========================================================================
# POST — Erros 400
# ===========================================================================


class TestPostGruposErros400:
    def test_parcela_total_menor_que_2_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/grupos",
                json={**BODY_POST_VALIDO, "parcela_total": 1},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()
        repo.criar_lote.assert_not_awaited()

    def test_valor_parcela_zero_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/grupos",
                json={**BODY_POST_VALIDO, "valor_parcela": "0.00"},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()
        repo.criar_lote.assert_not_awaited()

    def test_valor_parcela_negativo_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/grupos",
                json={**BODY_POST_VALIDO, "valor_parcela": "-50.00"},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()
        repo.criar_lote.assert_not_awaited()

    def test_descricao_ausente_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        body = {k: v for k, v in BODY_POST_VALIDO.items() if k != "descricao"}
        with stack:
            resp = client.post("/api/grupos", json=body)

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "descricao" in corpo["erro"]

    def test_proxima_data_ausente_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        body = {k: v for k, v in BODY_POST_VALIDO.items() if k != "proxima_data"}
        with stack:
            resp = client.post("/api/grupos", json=body)

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "proxima_data" in corpo["erro"]

    def test_valor_parcela_ausente_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        body = {k: v for k, v in BODY_POST_VALIDO.items() if k != "valor_parcela"}
        with stack:
            resp = client.post("/api/grupos", json=body)

        assert resp.status_code == 400
        corpo = resp.json()
        assert "erro" in corpo
        assert "valor_parcela" in corpo["erro"]

    def test_parcela_atual_maior_que_total_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/grupos",
                json={**BODY_POST_VALIDO, "parcela_atual": 13, "parcela_total": 12},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()
        repo.criar_lote.assert_not_awaited()

    def test_parcela_atual_zero_retorna_400(self):
        repo = repo_padrao()
        client, stack = cliente_com(repo)
        with stack:
            resp = client.post(
                "/api/grupos",
                json={**BODY_POST_VALIDO, "parcela_atual": 0},
            )

        assert resp.status_code == 400
        assert "erro" in resp.json()
        repo.criar_lote.assert_not_awaited()
