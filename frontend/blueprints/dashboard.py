from flask import Blueprint, render_template, request

from frontend.config import CATEGORIAS, PERIODOS, TIPOS

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def index():
    return render_template(
        "dashboard/index.html",
        periodo=request.args.get("periodo", "mes_atual"),
        categorias=list(CATEGORIAS),
        tipos=list(TIPOS),
        periodos=PERIODOS,
    )


@bp.get("/health")
def health():
    return {"ok": True}
