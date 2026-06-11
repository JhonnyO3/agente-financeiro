import datetime


class RefreshStore:
    def __init__(self) -> None:
        self._ativos: dict[str, datetime.datetime] = {}

    def registrar(self, jti: str, exp: datetime.datetime) -> None:
        self._ativos[jti] = exp

    def ativo(self, jti: str) -> bool:
        exp = self._ativos.get(jti)
        if exp is None:
            return False
        if exp <= datetime.datetime.now(datetime.timezone.utc):
            self._ativos.pop(jti, None)
            return False
        return True

    def revogar(self, jti: str) -> None:
        self._ativos.pop(jti, None)
