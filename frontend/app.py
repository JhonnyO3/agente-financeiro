from flask import Flask

from frontend.blueprints import api_proxy, dashboard
from frontend.config import Settings
from frontend.services.backend_client import BackendClient


def create_app(settings: Settings | None = None) -> Flask:
    settings = settings or Settings()

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SETTINGS"] = settings
    app.config["BACKEND_CLIENT"] = BackendClient(
        base_url=settings.backend_url,
        timeout=settings.backend_timeout,
    )

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(api_proxy.bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(port=app.config["SETTINGS"].frontend_port)
