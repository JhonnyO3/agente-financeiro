"""Testes de render dos templates do dashboard (T06).

Cenários de specs/dashboard-flask/scenarios/ui.feature (T06):
- GET / retorna 200 com todos os ids do contrato js-interop
- Seletor de período tem 6 opções e marca a atual como selected
"""

import os
import re

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("EVOLUTION_API_URL", "http://localhost:8080")
os.environ.setdefault("EVOLUTION_INSTANCE", "test")
os.environ.setdefault("EVOLUTION_API_KEY", "test-key")
os.environ.setdefault("WHATSAPP_ALLOWED_NUMBER", "5511957818539")

import pytest

from dashboard.app import create_app

# Tabela de posse do DOM do contrato js-interop.md — todos obrigatórios.
IDS_OBRIGATORIOS = [
    "card-gastos",
    "card-investimentos",
    "card-saldo",
    "chart-pizza",
    "chart-barras",
    "chart-linha",
    "parcelas-container",
    "tabela-transacoes",
    "paginacao",
    "filtro-tipo",
    "filtro-categoria",
    "tabela-investimentos",
    "card-invest-periodo",
    "card-invest-total",
    "modal-editar",
    "modal-adicionar",
]


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_index_retorna_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_index_contem_todos_os_ids_do_contrato(client):
    html = client.get("/").get_data(as_text=True)
    faltando = [id_ for id_ in IDS_OBRIGATORIOS if f'id="{id_}"' not in html]
    assert not faltando, f"ids ausentes no HTML: {faltando}"


def test_seletor_periodo_tem_6_opcoes(client):
    html = client.get("/").get_data(as_text=True)
    select = _extrai_select_periodo(html)
    assert len(re.findall(r"<option\b", select)) == 6


def test_seletor_periodo_marca_opcao_atual_como_selected(client):
    html = client.get("/?periodo=ano_atual").get_data(as_text=True)
    select = _extrai_select_periodo(html)
    selecionadas = re.findall(r'<option[^>]*\bselected\b[^>]*>', select)
    assert len(selecionadas) == 1
    assert 'value="ano_atual"' in selecionadas[0]


def test_seletor_periodo_padrao_mes_atual(client):
    html = client.get("/").get_data(as_text=True)
    select = _extrai_select_periodo(html)
    selecionadas = re.findall(r'<option[^>]*\bselected\b[^>]*>', select)
    assert len(selecionadas) == 1
    assert 'value="mes_atual"' in selecionadas[0]


def test_scripts_carregados_na_ordem_do_contrato(client):
    html = client.get("/").get_data(as_text=True)
    posicoes = [html.index(nome) for nome in ("charts.js", "table.js", "app.js")]
    assert posicoes == sorted(posicoes)


def test_filtros_da_tabela_tem_todas_as_opcoes(client):
    html = client.get("/").get_data(as_text=True)
    filtro_tipo = _extrai_select(html, "filtro-tipo")
    assert len(re.findall(r"<option\b", filtro_tipo)) == 3  # Todos + 2 tipos
    filtro_categoria = _extrai_select(html, "filtro-categoria")
    assert len(re.findall(r"<option\b", filtro_categoria)) == 9  # Todas + 8 categorias


def _extrai_select_periodo(html: str) -> str:
    match = re.search(r'<select[^>]*name="periodo".*?</select>', html, re.DOTALL)
    assert match, "select de período não encontrado"
    return match.group(0)


def _extrai_select(html: str, id_: str) -> str:
    match = re.search(rf'<select[^>]*id="{id_}".*?</select>', html, re.DOTALL)
    assert match, f"select #{id_} não encontrado"
    return match.group(0)
