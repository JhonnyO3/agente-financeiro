"""Factory da aplicação Flask do dashboard.

Execução local: uv run flask --app dashboard.app run
"""

import importlib

from flask import Flask, render_template, request

from app.models.enums import CategoriaEnum, TipoEnum

# Decisão 11 do plan.md: registro dinâmico — cada módulo expõe a variável
# `bp`; módulos ausentes (tarefas paralelas ainda não integradas) são
# ignorados para que a app suba sozinha.
_BLUEPRINTS = (
    "api_resumo",
    "api_graficos",
    "api_parcelas",
    "api_transacoes",
    "api_projecao",
)

PERIODOS = {
    "mes_atual": "Mês atual",
    "mes_anterior": "Mês anterior",
    "ultimos_3_meses": "Últimos 3 meses",
    "ultimos_6_meses": "Últimos 6 meses",
    "ano_atual": "Ano atual",
    "tudo": "Tudo",
}


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    for nome in _BLUEPRINTS:
        try:
            modulo = importlib.import_module(f"dashboard.blueprints.{nome}")
        except ImportError:
            continue
        app.register_blueprint(modulo.bp)

    @app.get("/")
    def index():
        return render_template(
            "index.html",
            periodo=request.args.get("periodo", "mes_atual"),
            categorias=[categoria.value for categoria in CategoriaEnum],
            tipos=[tipo.value for tipo in TipoEnum],
            periodos=PERIODOS,
        )

    @app.get("/health")
    def health():
        return {"ok": True}

    return app


app = create_app()
