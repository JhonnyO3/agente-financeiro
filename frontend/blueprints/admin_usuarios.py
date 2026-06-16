import httpx
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

bp = Blueprint("admin_usuarios", __name__, url_prefix="/admin/usuarios")


def _cliente():
    return current_app.config["BACKEND_CLIENT"]


def _exige_admin():
    if session.get("role") != "ADMIN":
        return redirect(url_for("auth.login_form"))
    return None


@bp.get("/novo")
def novo_form():
    guard = _exige_admin()
    if guard:
        return guard
    return render_template("admin/usuarios_novo.html")


@bp.post("/novo")
def novo_submit():
    guard = _exige_admin()
    if guard:
        return guard

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    telefone = request.form.get("telefone", "").strip()
    senha = request.form.get("senha", "").strip()

    # validações locais
    erro = None
    if not nome:
        erro = "O nome é obrigatório."
    elif "@" not in email:
        erro = "E-mail inválido."
    elif not telefone.isdigit() or not (10 <= len(telefone) <= 15):
        erro = "Telefone inválido: use somente dígitos (10 a 15 caracteres)."
    elif not senha:
        erro = "A senha é obrigatória."

    if erro:
        return render_template(
            "admin/usuarios_novo.html",
            erro=erro,
            nome=nome,
            email=email,
            telefone=telefone,
        )

    username = email.split("@")[0]
    body = {
        "nome": nome,
        "username": username,
        "email": email,
        "senha": senha,
        "telefone": telefone,
        "role": "USER",
    }

    try:
        resposta = _cliente().criar_usuario(body)
    except httpx.HTTPError:
        return render_template(
            "admin/usuarios_novo.html",
            erro="Backend indisponível.",
            nome=nome,
            email=email,
            telefone=telefone,
        )

    if resposta.status_code == 201:
        flash("Usuário cadastrado com sucesso!")
        return redirect(url_for("dashboard.index"))

    if resposta.status_code == 409:
        return render_template(
            "admin/usuarios_novo.html",
            erro="Este e-mail já está cadastrado.",
            nome=nome,
            email=email,
            telefone=telefone,
        )

    return render_template(
        "admin/usuarios_novo.html",
        erro="Dados inválidos.",
        nome=nome,
        email=email,
        telefone=telefone,
    )
