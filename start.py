import os
import signal
import subprocess
import sys
import threading

BACKEND_CMD = ["uv", "run", "uvicorn", "backend.main:app", "--port", "8000"]
FRONTEND_CMD = ["uv", "run", "flask", "--app", "frontend.app", "run", "--port", "5000"]

IS_WINDOWS = os.name == "nt"


def construir_comandos():
    return [("backend", BACKEND_CMD), ("frontend", FRONTEND_CMD)]


def prefixar_linha(prefixo, linha):
    return f"[{prefixo}] {linha.rstrip()}"


def _flags_criacao():
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def iniciar_processo(comando):
    return subprocess.Popen(
        comando,
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
    processos = []
    threads = []
    for prefixo, comando in construir_comandos():
        processo = iniciar_processo(comando)
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
