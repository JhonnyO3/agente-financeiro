from flask import session


def gravar_tokens(access_token: str, refresh_token: str, role: str, email: str) -> None:
    session["access_token"] = access_token
    session["refresh_token"] = refresh_token
    session["role"] = role
    session["email"] = email


def atualizar_tokens(access_token: str, refresh_token: str) -> None:
    session["access_token"] = access_token
    session["refresh_token"] = refresh_token


def access_token() -> str | None:
    return session.get("access_token")


def refresh_token() -> str | None:
    return session.get("refresh_token")


def esta_autenticado() -> bool:
    return "access_token" in session


def limpar() -> None:
    session.clear()
