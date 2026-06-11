import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test"
)

from contextlib import ExitStack
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.auth.dependencies import UsuarioToken, get_usuario_atual
from backend.dependencies import get_session
from backend.main import app


def _override_session():
    async def _fake():
        yield SimpleNamespace()

    async def _fake_usuario():
        return UsuarioToken(usuario_id=1, role="USER", email="user@exemplo.com")

    app.dependency_overrides[get_session] = _fake
    app.dependency_overrides[get_usuario_atual] = _fake_usuario


def cliente_com(transacoes):
    _override_session()
    repo = SimpleNamespace(listar_por_periodo=AsyncMock(return_value=transacoes))
    stack = ExitStack()
    stack.enter_context(
        patch("backend.services.resumo.TransacaoRepository", lambda session: repo)
    )
    stack.callback(app.dependency_overrides.clear)
    return TestClient(app), stack


def make_transacao(tipo, categoria, valor):
    return SimpleNamespace(
        tipo=tipo,
        categoria=categoria,
        valor=Decimal(valor),
        data=date(2026, 6, 1),
    )


def test_resumo_formato_e_valores_string():
    transacoes = [
        make_transacao("GASTO", "ALIMENTACAO", "100.00"),
        make_transacao("GASTO", "TRANSPORTE", "50.00"),
        make_transacao("RECEITA", "RECEITA", "500.00"),
        make_transacao("INVESTIMENTO", "INVESTIMENTO", "200.00"),
    ]
    client, stack = cliente_com(transacoes)
    with stack:
        resposta = client.get("/api/resumo?periodo=mes_atual")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert set(corpo) == {"gastos", "receitas", "investimentos", "saldo", "periodo"}
    assert corpo["gastos"] == "150.00"
    assert corpo["receitas"] == "500.00"
    assert corpo["investimentos"] == "200.00"
    assert corpo["saldo"] == "150.00"
    assert corpo["periodo"] == "mes_atual"
    for chave in ("gastos", "receitas", "investimentos", "saldo"):
        assert isinstance(corpo[chave], str)


def test_resumo_periodo_default_mes_atual():
    client, stack = cliente_com([])
    with stack:
        resposta = client.get("/api/resumo")

    assert resposta.json()["periodo"] == "mes_atual"


def test_resumo_vazio_zera_valores():
    client, stack = cliente_com([])
    with stack:
        resposta = client.get("/api/resumo?periodo=tudo")

    corpo = resposta.json()
    assert corpo["gastos"] == "0.00"
    assert corpo["saldo"] == "0.00"


def test_categorias_so_de_gasto():
    transacoes = [
        make_transacao("GASTO", "ALIMENTACAO", "75.00"),
        make_transacao("GASTO", "ALIMENTACAO", "25.00"),
        make_transacao("GASTO", "TRANSPORTE", "100.00"),
        make_transacao("INVESTIMENTO", "INVESTIMENTO", "999.00"),
        make_transacao("RECEITA", "RECEITA", "999.00"),
    ]
    client, stack = cliente_com(transacoes)
    with stack:
        resposta = client.get("/api/grafico/categorias")

    itens = resposta.json()
    categorias = {item["categoria"] for item in itens}
    assert categorias == {"ALIMENTACAO", "TRANSPORTE"}

    por_categoria = {item["categoria"]: item for item in itens}
    assert por_categoria["ALIMENTACAO"]["total"] == "100.00"
    assert por_categoria["TRANSPORTE"]["total"] == "100.00"
    assert por_categoria["ALIMENTACAO"]["percentual"] == 50.0


def test_categorias_ordenado_desc_por_total():
    transacoes = [
        make_transacao("GASTO", "ALIMENTACAO", "30.00"),
        make_transacao("GASTO", "TRANSPORTE", "70.00"),
    ]
    client, stack = cliente_com(transacoes)
    with stack:
        resposta = client.get("/api/grafico/categorias")

    itens = resposta.json()
    assert [item["categoria"] for item in itens] == ["TRANSPORTE", "ALIMENTACAO"]


def test_categorias_vazio_retorna_lista_vazia():
    transacoes = [make_transacao("INVESTIMENTO", "INVESTIMENTO", "100.00")]
    client, stack = cliente_com(transacoes)
    with stack:
        resposta = client.get("/api/grafico/categorias")

    assert resposta.json() == []


def test_resolver_periodo_tudo_cobre_o_futuro():
    from backend.services.resumo import resolver_periodo

    inicio, fim = resolver_periodo("tudo")
    assert inicio == date(2000, 1, 1)
    assert fim >= date(2099, 1, 1)


def test_resolver_periodo_mes_atual_vai_ate_fim_do_mes():
    from datetime import timedelta

    from backend.services.resumo import resolver_periodo

    hoje = date.today()
    inicio, fim = resolver_periodo("mes_atual")
    assert inicio == date(hoje.year, hoje.month, 1)
    assert fim >= hoje
    assert (fim + timedelta(days=1)).month != hoje.month


def test_resolver_periodo_ano_atual_vai_ate_dezembro():
    from backend.services.resumo import resolver_periodo

    hoje = date.today()
    _, fim = resolver_periodo("ano_atual")
    assert fim == date(hoje.year, 12, 31)
