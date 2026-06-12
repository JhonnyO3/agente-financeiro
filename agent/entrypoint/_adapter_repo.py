from backend.repositories.transacao_repository import TransacaoRepository


class AdapterRepo:
    """Adapter que envolve um repository já instanciado com usuario_id fixo."""

    def __init__(self, repo, usuario_id: int) -> None:
        self._repo = repo
        self._usuario_id = usuario_id

    async def buscar_semantico_multiplos_com_distancia(self, embedding, limite=5):
        return await self._repo.buscar_semantico_multiplos_com_distancia(
            embedding, limite=limite, usuario_id=self._usuario_id
        )


class SessionFactoryAdapterRepo:
    """Adapter baseado em session_factory com usuario_id fixo."""

    def __init__(self, session_factory, usuario_id: int) -> None:
        self._session_factory = session_factory
        self._usuario_id = usuario_id

    def _repo(self, session):
        return TransacaoRepository(session)

    async def buscar_semantico_multiplos_com_distancia(self, embedding, limite=5):
        async with self._session_factory() as session:
            return await self._repo(session).buscar_semantico_multiplos_com_distancia(
                embedding, limite=limite, usuario_id=self._usuario_id
            )
