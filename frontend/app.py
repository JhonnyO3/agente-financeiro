from flask import Flask, jsonify, redirect, request, url_for

from frontend.blueprints import api_proxy, auth, dashboard
from frontend.config import Settings
from frontend.services import sessao
from frontend.services.backend_client import BackendClient

_ROTAS_PUBLICAS = {"auth.login_form", "auth.login", "auth.logout", "static"}
_CAMINHOS_PUBLICOS = {"/login", "/logout", "/health"}


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = settings.secret_key
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = settings.session_cookie_secure
    app.config["SETTINGS"] = settings
    app.config["BACKEND_CLIENT"] = BackendClient(
        base_url=settings.backend_url,
        timeout=settings.backend_timeout,
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(api_proxy.bp)

    @app.before_request
    def proteger_rotas():
        if request.endpoint in _ROTAS_PUBLICAS:
            return None
        if request.path in _CAMINHOS_PUBLICOS:
            return None
        if sessao.esta_autenticado():
            return None
        if request.path.startswith("/api/"):
            return jsonify({"erro": "não autenticado"}), 401
        return redirect(url_for("auth.login_form"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=app.config["SETTINGS"].frontend_port)
