"""Sobe backend (FastAPI) e frontend (React/Vite) simultaneamente para dev local.

Uso:
    uv run python start.py

- backend  : uvicorn backend.main:app  -> http://127.0.0.1:8000
- frontend : react-dashboard (Vite)    -> http://127.0.0.1:5173

O Vite faz proxy de /api, /auth e /admin para o backend (ver vite.config.js).
Encerra ambos os processos com Ctrl+C.

O agente do WhatsApp (agent.entrypoint.main) NAO sobe aqui — depende de Redis e da
Evolution API. Rode-o separadamente quando precisar:
    uv run uvicorn agent.entrypoint.main:app --host 127.0.0.1 --port 8001
"""

import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REACT_DIR = RAIZ / "react-dashboard"

IS_WINDOWS = os.name == "nt"


def _npm() -> str:
    # No Windows o executavel e npm.cmd; shutil.which resolve o caminho completo.
    return shutil.which("npm.cmd" if IS_WINDOWS else "npm") or "npm"


BACKEND_CMD = ["uv", "run", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"]
FRONTEND_CMD = [_npm(), "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"]


def construir_comandos():
    return [
        ("backend", BACKEND_CMD, RAIZ),
        ("frontend", FRONTEND_CMD, REACT_DIR),
    ]


def prefixar_linha(prefixo, linha):
    return f"[{prefixo}] {linha.rstrip()}"


def _flags_criacao():
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def iniciar_processo(comando, cwd):
    return subprocess.Popen(
        comando,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        **_flags_criacao(),
    )


def encaminhar_saida(prefixo, processo, stream=None):
    destino = stream or sys.stdout
    for linha in iter(processo.stdout.readline, ""):
        if not linha:
            break
        print(prefixar_linha(prefixo, linha), file=destino, flush=True)


def _interromper(processo):
    if processo.poll() is not None:
        return
    if IS_WINDOWS:
        processo.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        processo.send_signal(signal.SIGINT)


def encerrar(processos, timeout=10):
    for _, processo in processos:
        _interromper(processo)
    for _, processo in processos:
        try:
            processo.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            processo.kill()


def main():
    print("Backend : http://127.0.0.1:8000  (health: /health)", flush=True)
    print("Frontend: http://127.0.0.1:5173  (use 127.0.0.1, nao 'localhost' — evita atraso de IPv6)", flush=True)
    processos = []
    threads = []
    for prefixo, comando, cwd in construir_comandos():
        processo = iniciar_processo(comando, cwd)
        processos.append((prefixo, processo))
        thread = threading.Thread(
            target=encaminhar_saida, args=(prefixo, processo), daemon=True
        )
        thread.start()
        threads.append(thread)

    try:
        while any(processo.poll() is None for _, processo in processos):
            for _, processo in processos:
                try:
                    processo.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    continue
    except KeyboardInterrupt:
        pass
    finally:
        encerrar(processos)


if __name__ == "__main__":
    main()
