from passlib.context import CryptContext

_contexto = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    return _contexto.hash(senha)


def verificar_senha(senha: str, hash: str) -> bool:
    try:
        return _contexto.verify(senha, hash)
    except ValueError:
        return False
