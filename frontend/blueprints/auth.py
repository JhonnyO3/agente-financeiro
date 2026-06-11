import httpx
from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    url_for,
)

from frontend.services import sessao

bp = Blueprint("auth", __name__)


def _cliente():
    return current_app.config["BACKEND_CLIENT"]


@bp.get("/login")
def login_form():
    return render_template("auth/login.html")


@bp.post("/login")
def login():
    email = request.form.get("email", "")
    senha = request.form.get("senha", "")

    try:
        resposta = _cliente().login(email, senha)
    except httpx.HTTPError:
        return render_template("auth/login.html", erro="Backend indisponível."), 503

    if resposta.status_code != 200:
        return (
            render_template("auth/login.html", erro="Credenciais inválidas."),
            401,
        )

    dados = resposta.json()
    sessao.gravar_tokens(
        access_token=dados["access_token"],
        refresh_token=dados["refresh_token"],
        role=dados.get("role", "USER"),
        email=email,
    )
    return redirect(url_for("dashboard.index"))


@bp.route("/logout", methods=["GET", "POST"])
def logout():
    refresh = sessao.refresh_token()
    if refresh:
        try:
            _cliente().logout(refresh)
        except httpx.HTTPError:
            pass
    sessao.limpar()
    return redirect(url_for("auth.login_form"))
