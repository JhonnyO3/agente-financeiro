from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


class Relogio:
    """Relógio injetável com fuso do usuário. _fixed permite fixar o instante em testes."""

    def __init__(self, tz: str, _fixed: datetime | None = None) -> None:
        self._tz = ZoneInfo(tz)
        self._fixed = _fixed

    def agora(self) -> datetime:
        utc_now = (
            self._fixed if self._fixed is not None else datetime.now(tz=timezone.utc)
        )
        return utc_now.astimezone(self._tz)

    def hoje(self) -> date:
        return self.agora().date()
