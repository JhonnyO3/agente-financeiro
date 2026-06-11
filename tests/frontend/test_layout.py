import re
from pathlib import Path


def test_index_renderiza_selects(client):
    resp = client.get("/")
    html = resp.get_data(as_text=True)

    assert resp.status_code == 200
    assert 'id="seletor-periodo"' in html
    assert 'id="filtro-categoria"' in html
    assert 'id="filtro-tipo"' in html
    assert "ALIMENTACAO" in html
    assert "GASTO" in html
    assert "Mês atual" in html


def test_index_usa_caminhos_static_js(client):
    html = client.get("/").get_data(as_text=True)

    assert "/static/js/charts.js" in html
    assert "/static/js/table.js" in html
    assert "/static/js/app.js" in html
    assert "/static/css/app.css" in html


def test_index_tem_container_centralizado():
    base = Path(__file__).resolve().parents[2] / "frontend" / "templates" / "base.html"
    conteudo = base.read_text(encoding="utf-8")
    assert "app-container" in conteudo


def test_css_layout_max_width_margin_e_borda():
    css = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "static"
        / "css"
        / "app.css"
    ).read_text(encoding="utf-8")

    assert "max-width: 1400px" in css
    assert "margin: 0 auto" in css
    assert re.search(r"border:\s*1px", css)
    assert "@media (max-width: 1400px)" in css
    assert "overflow-x: hidden" in css


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
