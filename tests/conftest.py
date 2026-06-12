"""
Fixtures de infraestrutura para a suite de testes.

Garante isolamento de variáveis de ambiente entre módulos de teste
que importam Settings em diferentes contextos.
"""

from __future__ import annotations

import os
from typing import Generator

import pytest

# Variáveis cujo valor canônico deve prevalecer para os testes do webhook worker.
# test_agente_isolamento.py e outros setam WHATSAPP_ALLOWED_NUMBER com valores
# diferentes via setdefault, mas os testes de webhook precisam do número
# correto em tempo de execução (os.environ é lido em cada request).
_WEBHOOK_ENV_CANONICAL = {
    "WHATSAPP_ALLOWED_NUMBER": "5511957818539",
    "WEBHOOK_APIKEY": "test-apikey",
}


@pytest.fixture(autouse=True)
def _reset_env_webhook(request: pytest.FixtureRequest) -> Generator[None, None, None]:
    """
    Para testes do webhook worker, garante isolamento completo:
    - env vars reflitam os valores canônicos do test_webhook_worker.py
    - dict de dedup (_seen) seja limpo entre testes
    Não afeta outros módulos de teste.
    """
    if "test_webhook_worker" not in request.node.nodeid:
        yield
        return

    # Env vars: salva original e força o valor canônico
    original_env = {k: os.environ.get(k) for k in _WEBHOOK_ENV_CANONICAL}
    for k, v in _WEBHOOK_ENV_CANONICAL.items():
        os.environ[k] = v

    # Dedup dict: limpa antes do teste
    from agent.entrypoint import webhook as _wh

    _wh._seen.clear()

    yield

    # Restaura env vars
    for k, orig_v in original_env.items():
        if orig_v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig_v

    # Limpa dedup após o teste (isolamento)
    _wh._seen.clear()
