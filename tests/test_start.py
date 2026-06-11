from unittest.mock import MagicMock

import start


def test_construir_comandos_inclui_backend_e_frontend():
    comandos = dict(start.construir_comandos())

    assert comandos["backend"] == [
        "uv",
        "run",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    assert comandos["frontend"] == [
        "uv",
        "run",
        "flask",
        "--app",
        "frontend.app",
        "run",
        "--host",
        "127.0.0.1",
        "--port",
        "5000",
    ]


def test_prefixar_linha_aplica_prefixo_e_remove_quebra():
    assert start.prefixar_linha("backend", "subindo\n") == "[backend] subindo"
    assert start.prefixar_linha("frontend", "ok") == "[frontend] ok"


def test_iniciar_processo_usa_popen_com_pipe(monkeypatch):
    capturado = {}

    def fake_popen(comando, **kwargs):
        capturado["comando"] = comando
        capturado["kwargs"] = kwargs
        return MagicMock()

    monkeypatch.setattr(start.subprocess, "Popen", fake_popen)

    start.iniciar_processo(["uv", "run", "x"])

    assert capturado["comando"] == ["uv", "run", "x"]
    assert capturado["kwargs"]["stdout"] is start.subprocess.PIPE
    assert capturado["kwargs"]["stderr"] is start.subprocess.STDOUT


def test_encaminhar_saida_prefixa_cada_linha(capsys):
    processo = MagicMock()
    processo.stdout.readline = MagicMock(side_effect=["linha 1\n", "linha 2\n", ""])

    start.encaminhar_saida("backend", processo)

    saida = capsys.readouterr().out.splitlines()
    assert saida == ["[backend] linha 1", "[backend] linha 2"]


def test_encerrar_aguarda_e_mata_no_timeout():
    vivo = MagicMock()
    vivo.poll.return_value = None
    vivo.wait.side_effect = start.subprocess.TimeoutExpired(cmd="x", timeout=10)

    encerrado = MagicMock()
    encerrado.poll.return_value = 0

    start.encerrar([("backend", vivo), ("frontend", encerrado)], timeout=1)

    vivo.kill.assert_called_once()
    encerrado.kill.assert_not_called()
