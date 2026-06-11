import httpx


def test_resumo_repassa_querystring_e_status(client, backend, resposta_factory):
    backend.resumo.return_value = resposta_factory(
        200, {"gastos": "10.00", "periodo": "mes_atual"}
    )

    resp = client.get("/api/resumo?periodo=ultimos_3_meses")

    assert resp.status_code == 200
    assert resp.get_json() == {"gastos": "10.00", "periodo": "mes_atual"}
    backend.resumo.assert_called_once_with({"periodo": "ultimos_3_meses"})


def test_repassa_status_de_erro_do_backend(client, backend, resposta_factory):
    backend.criar_transacao.return_value = resposta_factory(
        400, {"erro": "Campos invalidos"}
    )

    resp = client.post("/api/transacoes", json={"valor": "abc"})

    assert resp.status_code == 400
    assert resp.get_json() == {"erro": "Campos invalidos"}


def test_post_repassa_body(client, backend, resposta_factory):
    backend.criar_transacao.return_value = resposta_factory(201, {"id": 1, "ok": True})

    corpo = {"data": "2026-06-10", "valor": "10.00", "tipo": "GASTO", "categoria": "LAZER"}
    resp = client.post("/api/transacoes", json=corpo)

    assert resp.status_code == 201
    backend.criar_transacao.assert_called_once_with(corpo)


def test_put_repassa_id_e_body(client, backend, resposta_factory):
    backend.atualizar_transacao.return_value = resposta_factory(200, {"ok": True})

    resp = client.put("/api/transacoes/42", json={"valor": "5.00"})

    assert resp.status_code == 200
    backend.atualizar_transacao.assert_called_once_with(42, {"valor": "5.00"})


def test_delete_grupo_repassa_id(client, backend, resposta_factory):
    backend.excluir_grupo.return_value = resposta_factory(200, {"ok": True, "removidos": 3})

    resp = client.delete("/api/grupos/abc-123")

    assert resp.status_code == 200
    backend.excluir_grupo.assert_called_once_with("abc-123")


def test_evolucao_proxia(client, backend, resposta_factory):
    backend.grafico_evolucao.return_value = resposta_factory(
        200, [{"mes": "Jun/26", "gastos": "1.00", "investimentos": "2.00", "receitas": "3.00"}]
    )

    resp = client.get("/api/grafico/evolucao")

    assert resp.status_code == 200
    assert resp.get_json()[0]["receitas"] == "3.00"


def test_backend_indisponivel_vira_502(client, backend):
    backend.resumo.side_effect = httpx.ConnectError("recusou conexão")

    resp = client.get("/api/resumo")

    assert resp.status_code == 502
    assert resp.get_json() == {"erro": "backend indisponível"}


def test_timeout_vira_502(client, backend):
    backend.listar_transacoes.side_effect = httpx.TimeoutException("estourou")

    resp = client.get("/api/transacoes?periodo=tudo")

    assert resp.status_code == 502
    assert resp.get_json() == {"erro": "backend indisponível"}
