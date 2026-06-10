"""Testes de render dos templates do dashboard (T06 + T08).

Cenários de specs/dashboard-flask/scenarios/ui.feature (T06) e
specs/melhorias-dashboard/scenarios/08-front-base.feature (T08):
- GET / retorna 200 com todos os ids dos contratos js-interop e dom-v2
- Seletor de período tem 6 opções e marca a atual como selected
- Filtros, theads e campos dos modais conforme contrato dom-v2
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

# Tabela de posse do DOM dos contratos js-interop.md + dom-v2.md — todos obrigatórios.
IDS_OBRIGATORIOS = [
    "card-gastos",
    "card-receitas",
    "card-investimentos",
    "card-saldo",
    "chart-pizza",
    "chart-barras",
    "chart-linha",
    "projecao-container",
    "parcelas-container",
    "tabela-transacoes",
    "paginacao",
    "filtro-tipo",
    "filtro-categoria",
    "filtro-status",
    "tabela-investimentos",
    "card-invest-periodo",
    "card-invest-total",
    "modal-editar",
    "modal-adicionar",
    "edit-status",
    "edit-forma-pagamento",
    "edit-responsavel",
    "edit-detalhes",
    "add-status",
    "add-forma-pagamento",
    "add-responsavel",
    "add-detalhes",
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
    assert len(re.findall(r"<option\b", filtro_tipo)) == 4  # Todos + 3 tipos
    assert 'value="RECEITA"' in filtro_tipo
    filtro_categoria = _extrai_select(html, "filtro-categoria")
    assert len(re.findall(r"<option\b", filtro_categoria)) == 10  # Todas + 9 categorias


def test_filtro_status_tem_3_opcoes(client):
    html = client.get("/").get_data(as_text=True)
    filtro_status = _extrai_select(html, "filtro-status")
    assert len(re.findall(r"<option\b", filtro_status)) == 3  # Todos + PAGO/PENDENTE
    assert 'value="PAGO"' in filtro_status
    assert 'value="PENDENTE"' in filtro_status


def test_theads_tem_colunas_status_e_responsavel(client):
    html = client.get("/").get_data(as_text=True)
    for tabela_id in ("tabela-transacoes", "tabela-investimentos"):
        thead = _extrai_thead(html, tabela_id)
        colunas = re.findall(r"<th[^>]*>(.*?)</th>", thead, re.DOTALL)
        colunas = [coluna.strip() for coluna in colunas]
        assert "Status" in colunas, f"coluna Status ausente em #{tabela_id}"
        assert "Responsável" in colunas, f"coluna Responsável ausente em #{tabela_id}"
        # Status e Responsável ficam entre Tipo e Ações (contrato dom-v2).
        assert (
            colunas.index("Tipo")
            < colunas.index("Status")
            < colunas.index("Responsável")
            < colunas.index("Ações")
        ), f"ordem das colunas incorreta em #{tabela_id}: {colunas}"


def test_modais_tem_selects_de_status_e_forma_pagamento(client):
    html = client.get("/").get_data(as_text=True)
    for prefixo in ("edit", "add"):
        status = _extrai_select(html, f"{prefixo}-status")
        assert 'value="PAGO"' in status
        assert 'value="PENDENTE"' in status
        forma = _extrai_select(html, f"{prefixo}-forma-pagamento")
        assert 'value="PIX"' in forma
        assert 'value="CARTAO_CREDITO"' in forma
        assert 'value="CARTAO_DEBITO"' in forma
        assert 'value="BOLETO"' in forma
        assert 'value="OUTRO"' not in forma


def test_projecao_tem_titulo(client):
    html = client.get("/").get_data(as_text=True)
    assert "Projeção — próximos 6 meses" in html


def _extrai_select_periodo(html: str) -> str:
    match = re.search(r'<select[^>]*name="periodo".*?</select>', html, re.DOTALL)
    assert match, "select de período não encontrado"
    return match.group(0)


def _extrai_select(html: str, id_: str) -> str:
    match = re.search(rf'<select[^>]*id="{id_}".*?</select>', html, re.DOTALL)
    assert match, f"select #{id_} não encontrado"
    return match.group(0)


def _extrai_thead(html: str, tabela_id: str) -> str:
    match = re.search(rf'<table[^>]*id="{tabela_id}".*?</thead>', html, re.DOTALL)
    assert match, f"thead da tabela #{tabela_id} não encontrado"
    return match.group(0)
