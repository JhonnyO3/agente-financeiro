import os
from unittest.mock import MagicMock

import httpx
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")

from frontend.app import create_app
from frontend.config import Settings


def _resposta(status: int, payload, content_type: str = "application/json"):
    import json

    resposta = MagicMock(spec=httpx.Response)
    resposta.status_code = status
    resposta.content = json.dumps(payload).encode()
    resposta.headers = {"content-type": content_type}
    return resposta


@pytest.fixture
def backend():
    return MagicMock()


@pytest.fixture
def client(backend):
    app = create_app(
        Settings(
            backend_url="http://backend.test",
            frontend_port=5000,
            secret_key="test-secret",
        )
    )
    app.config["BACKEND_CLIENT"] = backend
    app.config["TESTING"] = True
    test_client = app.test_client()
    with test_client.session_transaction() as sessao:
        sessao["access_token"] = "token-teste"
        sessao["refresh_token"] = "refresh-teste"
        sessao["role"] = "USER"
        sessao["email"] = "tester@example.com"
    return test_client


@pytest.fixture
def resposta_factory():
    return _resposta
