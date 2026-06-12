"""
Testes T06 — UI da seção "Gastos fixos" no dashboard.

Verificam que o partial _gastos_fixos.html é renderizado pelo Flask com todos
os IDs exigidos pelo contrato frontend-dashboard.md, e que gastos_fixos.js
é carregado pela página.
"""


# ---------------------------------------------------------------------------
# IDs do contrato — seção gastos fixos
# ---------------------------------------------------------------------------

_IDS_SECAO = [
    "gastos-fixos-container",
    "gastos-fixos-total",
    "gastos-fixos-vazio",
    "btn-novo-gasto-fixo",
]

_IDS_MODAL = [
    "modal-gasto-fixo",
    "gf-descricao",
    "gf-valor",
    "gf-data",
    "gf-categoria",
    "gf-forma-pagamento",
    "gf-responsavel",
    "gf-id",
    "btn-salvar-gasto-fixo",
    "gf-erro",
]

_TEXTO_VAZIO = "Nenhum gasto fixo cadastrado"


def _html(client):
    return client.get("/").get_data(as_text=True)


# ---------------------------------------------------------------------------
# Presença dos IDs da seção
# ---------------------------------------------------------------------------


def test_gastos_fixos_container_presente(client):
    assert 'id="gastos-fixos-container"' in _html(client)


def test_gastos_fixos_total_presente(client):
    assert 'id="gastos-fixos-total"' in _html(client)


def test_gastos_fixos_vazio_presente(client):
    assert 'id="gastos-fixos-vazio"' in _html(client)


def test_btn_novo_gasto_fixo_presente(client):
    assert 'id="btn-novo-gasto-fixo"' in _html(client)


def test_texto_vazio_correto(client):
    assert _TEXTO_VAZIO in _html(client)


# ---------------------------------------------------------------------------
# Presença dos IDs do modal
# ---------------------------------------------------------------------------


def test_modal_gasto_fixo_presente(client):
    assert 'id="modal-gasto-fixo"' in _html(client)


def test_gf_descricao_presente(client):
    assert 'id="gf-descricao"' in _html(client)


def test_gf_valor_presente(client):
    assert 'id="gf-valor"' in _html(client)


def test_gf_valor_inputmode_decimal(client):
    assert 'inputmode="decimal"' in _html(client)


def test_gf_data_presente(client):
    assert 'id="gf-data"' in _html(client)


def test_gf_data_type_date(client):
    html = _html(client)
    # Verifica que gf-data é type=date
    assert 'id="gf-data"' in html
    # O atributo type=date deve aparecer próximo ao id
    idx = html.index('id="gf-data"')
    trecho = html[max(0, idx - 60) : idx + 60]
    assert "date" in trecho


def test_gf_categoria_presente(client):
    assert 'id="gf-categoria"' in _html(client)


def test_gf_forma_pagamento_presente(client):
    assert 'id="gf-forma-pagamento"' in _html(client)


def test_gf_responsavel_presente(client):
    assert 'id="gf-responsavel"' in _html(client)


def test_gf_id_hidden_presente(client):
    html = _html(client)
    assert 'id="gf-id"' in html
    idx = html.index('id="gf-id"')
    trecho = html[max(0, idx - 60) : idx + 60]
    assert "hidden" in trecho


def test_btn_salvar_gasto_fixo_presente(client):
    assert 'id="btn-salvar-gasto-fixo"' in _html(client)


def test_gf_erro_presente(client):
    assert 'id="gf-erro"' in _html(client)


# ---------------------------------------------------------------------------
# Opções de forma de pagamento no modal
# ---------------------------------------------------------------------------


def test_forma_pagamento_tem_cartao_credito(client):
    html = _html(client)
    idx = html.index('id="gf-forma-pagamento"')
    bloco = html[idx : idx + 300]
    assert "CARTAO_CREDITO" in bloco


def test_forma_pagamento_tem_pix(client):
    html = _html(client)
    idx = html.index('id="gf-forma-pagamento"')
    bloco = html[idx : idx + 300]
    assert "PIX" in bloco


def test_forma_pagamento_tem_boleto(client):
    html = _html(client)
    idx = html.index('id="gf-forma-pagamento"')
    bloco = html[idx : idx + 300]
    assert "BOLETO" in bloco


def test_forma_pagamento_pix_default(client):
    html = _html(client)
    idx = html.index('id="gf-forma-pagamento"')
    bloco = html[idx : idx + 300]
    assert 'value="PIX" selected' in bloco or ">PIX<" in bloco


# ---------------------------------------------------------------------------
# gastos_fixos.js carregado pela página
# ---------------------------------------------------------------------------


def test_gastos_fixos_js_carregado(client):
    assert "gastos_fixos.js" in _html(client)


# ---------------------------------------------------------------------------
# Todos os IDs do contrato de uma vez (agregado)
# ---------------------------------------------------------------------------


def test_todos_ids_contrato_presentes(client):
    html = _html(client)
    ausentes = [id_ for id_ in _IDS_SECAO + _IDS_MODAL if f'id="{id_}"' not in html]
    assert ausentes == [], f"IDs ausentes no HTML renderizado: {ausentes}"
