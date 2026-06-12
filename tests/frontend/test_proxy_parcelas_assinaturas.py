"""
Testes TDD para T04 — Proxy Flask e cliente HTTP para os endpoints novos.

Cobrem:
  - PUT  /api/grupos/<grupo>      → backend.atualizar_grupo(grupo, body)
  - POST /api/grupos              → backend.criar_grupo(body)
  - GET  /api/gastos-fixos        → backend.listar_gastos_fixos()
  - POST /api/gastos-fixos        → backend.criar_gasto_fixo(body)
  - PUT  /api/gastos-fixos/<id>   → backend.atualizar_gasto_fixo(id, body)
  - DELETE /api/gastos-fixos/<id> → backend.excluir_gasto_fixo(id)
  - 502 em todas as rotas quando httpx.HTTPError
  - Não-regressão: DELETE /api/grupos/<grupo> existente
  - Verificação de presença dos 6 métodos novos em BackendClient (classe real)
"""

import httpx
import pytest

from frontend.services.backend_client import BackendClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BODY_GRUPO = {
    "descricao": "Notebook",
    "valor_parcela": "500.00",
    "proxima_data": "2026-07-05",
    "parcela_atual": 1,
    "parcela_total": 4,
}

_BODY_GASTO_FIXO = {
    "descricao": "Spotify",
    "valor": "19.90",
    "data": "2026-06-10",
}


# ===========================================================================
# Verificação estrutural — BackendClient deve ter os 6 métodos novos
# ===========================================================================


def test_backend_client_possui_atualizar_grupo():
    assert callable(getattr(BackendClient, "atualizar_grupo", None)), (
        "BackendClient não tem o método atualizar_grupo"
    )


def test_backend_client_possui_criar_grupo():
    assert callable(getattr(BackendClient, "criar_grupo", None)), (
        "BackendClient não tem o método criar_grupo"
    )


def test_backend_client_possui_listar_gastos_fixos():
    assert callable(getattr(BackendClient, "listar_gastos_fixos", None)), (
        "BackendClient não tem o método listar_gastos_fixos"
    )


def test_backend_client_possui_criar_gasto_fixo():
    assert callable(getattr(BackendClient, "criar_gasto_fixo", None)), (
        "BackendClient não tem o método criar_gasto_fixo"
    )


def test_backend_client_possui_atualizar_gasto_fixo():
    assert callable(getattr(BackendClient, "atualizar_gasto_fixo", None)), (
        "BackendClient não tem o método atualizar_gasto_fixo"
    )


def test_backend_client_possui_excluir_gasto_fixo():
    assert callable(getattr(BackendClient, "excluir_gasto_fixo", None)), (
        "BackendClient não tem o método excluir_gasto_fixo"
    )


# ===========================================================================
# PUT /api/grupos/<grupo>
# ===========================================================================


def test_put_grupos_repassa_200(client, backend, resposta_factory):
    backend.atualizar_grupo.return_value = resposta_factory(
        200, {"ok": True, "grupo_parcela_id": "grp-aaa", "parcela_total": 4}
    )

    resp = client.put("/api/grupos/grp-aaa", json=_BODY_GRUPO)

    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True, "grupo_parcela_id": "grp-aaa", "parcela_total": 4}
    backend.atualizar_grupo.assert_called_once_with("grp-aaa", _BODY_GRUPO)


def test_put_grupos_repassa_400(client, backend, resposta_factory):
    backend.atualizar_grupo.return_value = resposta_factory(
        400, {"erro": "ID inválido"}
    )

    resp = client.put("/api/grupos/nao-uuid", json={})

    assert resp.status_code == 400
    assert resp.get_json() == {"erro": "ID inválido"}


def test_put_grupos_repassa_404(client, backend, resposta_factory):
    backend.atualizar_grupo.return_value = resposta_factory(
        404, {"erro": "Grupo nao encontrado"}
    )

    resp = client.put("/api/grupos/grp-zzz", json=_BODY_GRUPO)

    assert resp.status_code == 404
    assert resp.get_json() == {"erro": "Grupo nao encontrado"}


def test_put_grupos_502_quando_backend_indisponivel(client, backend):
    backend.atualizar_grupo.side_effect = httpx.ConnectError("recusou")

    resp = client.put("/api/grupos/grp-aaa", json=_BODY_GRUPO)

    assert resp.status_code == 502
    assert resp.get_json() == {"erro": "backend indisponível"}


# ===========================================================================
# POST /api/grupos
# ===========================================================================


def test_post_grupos_repassa_201(client, backend, resposta_factory):
    backend.criar_grupo.return_value = resposta_factory(
        201, {"ok": True, "grupo_parcela_id": "novo-uuid", "parcela_total": 12}
    )

    resp = client.post("/api/grupos", json=_BODY_GRUPO)

    assert resp.status_code == 201
    assert resp.get_json() == {"ok": True, "grupo_parcela_id": "novo-uuid", "parcela_total": 12}
    backend.criar_grupo.assert_called_once_with(_BODY_GRUPO)


def test_post_grupos_repassa_400(client, backend, resposta_factory):
    backend.criar_grupo.return_value = resposta_factory(
        400, {"erro": "Campos obrigatorios ausentes: descricao"}
    )

    resp = client.post("/api/grupos", json={"valor_parcela": "100.00"})

    assert resp.status_code == 400
    assert resp.get_json() == {"erro": "Campos obrigatorios ausentes: descricao"}


def test_post_grupos_502_quando_backend_indisponivel(client, backend):
    backend.criar_grupo.side_effect = httpx.TimeoutException("timeout")

    resp = client.post("/api/grupos", json=_BODY_GRUPO)

    assert resp.status_code == 502
    assert resp.get_json() == {"erro": "backend indisponível"}


# ===========================================================================
# GET /api/gastos-fixos
# ===========================================================================


def test_get_gastos_fixos_repassa_200(client, backend, resposta_factory):
    payload = {
        "itens": [{"id": 1, "descricao": "Netflix", "valor": "45.90"}],
        "total_mensal": "45.90",
    }
    backend.listar_gastos_fixos.return_value = resposta_factory(200, payload)

    resp = client.get("/api/gastos-fixos")

    assert resp.status_code == 200
    corpo = resp.get_json()
    assert "itens" in corpo
    assert "total_mensal" in corpo
    backend.listar_gastos_fixos.assert_called_once_with()


def test_get_gastos_fixos_502_quando_backend_indisponivel(client, backend):
    backend.listar_gastos_fixos.side_effect = httpx.ConnectError("down")

    resp = client.get("/api/gastos-fixos")

    assert resp.status_code == 502
    assert resp.get_json() == {"erro": "backend indisponível"}


# ===========================================================================
# POST /api/gastos-fixos
# ===========================================================================


def test_post_gastos_fixos_repassa_201(client, backend, resposta_factory):
    backend.criar_gasto_fixo.return_value = resposta_factory(201, {"id": 42, "ok": True})

    resp = client.post("/api/gastos-fixos", json=_BODY_GASTO_FIXO)

    assert resp.status_code == 201
    assert resp.get_json() == {"id": 42, "ok": True}
    backend.criar_gasto_fixo.assert_called_once_with(_BODY_GASTO_FIXO)


def test_post_gastos_fixos_repassa_400(client, backend, resposta_factory):
    backend.criar_gasto_fixo.return_value = resposta_factory(
        400, {"erro": "Campos obrigatorios ausentes: valor"}
    )

    resp = client.post("/api/gastos-fixos", json={"descricao": "Spotify"})

    assert resp.status_code == 400
    assert resp.get_json() == {"erro": "Campos obrigatorios ausentes: valor"}


def test_post_gastos_fixos_502_quando_backend_indisponivel(client, backend):
    backend.criar_gasto_fixo.side_effect = httpx.ConnectError("down")

    resp = client.post("/api/gastos-fixos", json=_BODY_GASTO_FIXO)

    assert resp.status_code == 502
    assert resp.get_json() == {"erro": "backend indisponível"}


# ===========================================================================
# PUT /api/gastos-fixos/<int:id>
# ===========================================================================


def test_put_gastos_fixos_repassa_200(client, backend, resposta_factory):
    backend.atualizar_gasto_fixo.return_value = resposta_factory(200, {"ok": True})

    resp = client.put("/api/gastos-fixos/7", json={"descricao": "Novo nome"})

    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    backend.atualizar_gasto_fixo.assert_called_once_with(7, {"descricao": "Novo nome"})


def test_put_gastos_fixos_repassa_404(client, backend, resposta_factory):
    backend.atualizar_gasto_fixo.return_value = resposta_factory(
        404, {"erro": "Gasto fixo nao encontrado"}
    )

    resp = client.put("/api/gastos-fixos/99", json={})

    assert resp.status_code == 404
    assert resp.get_json() == {"erro": "Gasto fixo nao encontrado"}


def test_put_gastos_fixos_502_quando_backend_indisponivel(client, backend):
    backend.atualizar_gasto_fixo.side_effect = httpx.TimeoutException("timeout")

    resp = client.put("/api/gastos-fixos/7", json={"descricao": "x"})

    assert resp.status_code == 502
    assert resp.get_json() == {"erro": "backend indisponível"}


# ===========================================================================
# DELETE /api/gastos-fixos/<int:id>
# ===========================================================================


def test_delete_gastos_fixos_repassa_200(client, backend, resposta_factory):
    backend.excluir_gasto_fixo.return_value = resposta_factory(200, {"ok": True})

    resp = client.delete("/api/gastos-fixos/5")

    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    backend.excluir_gasto_fixo.assert_called_once_with(5)


def test_delete_gastos_fixos_repassa_404(client, backend, resposta_factory):
    backend.excluir_gasto_fixo.return_value = resposta_factory(
        404, {"erro": "Gasto fixo nao encontrado"}
    )

    resp = client.delete("/api/gastos-fixos/88")

    assert resp.status_code == 404
    assert resp.get_json() == {"erro": "Gasto fixo nao encontrado"}


def test_delete_gastos_fixos_502_quando_backend_indisponivel(client, backend):
    backend.excluir_gasto_fixo.side_effect = httpx.ConnectError("down")

    resp = client.delete("/api/gastos-fixos/5")

    assert resp.status_code == 502
    assert resp.get_json() == {"erro": "backend indisponível"}


# ===========================================================================
# Não-regressão: DELETE /api/grupos/<grupo> existente
# ===========================================================================


def test_delete_grupos_existente_nao_regride(client, backend, resposta_factory):
    backend.excluir_grupo.return_value = resposta_factory(
        200, {"ok": True, "removidos": 3}
    )

    resp = client.delete("/api/grupos/grp-aaa")

    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True, "removidos": 3}
    backend.excluir_grupo.assert_called_once_with("grp-aaa")
