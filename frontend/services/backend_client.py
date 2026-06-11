import httpx


class BackendClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self._base_url = base_url
        self._timeout = timeout

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self._base_url, timeout=self._timeout)

    def resumo(self, params: dict) -> httpx.Response:
        with self._client() as client:
            return client.get("/api/resumo", params=params)

    def grafico_categorias(self, params: dict) -> httpx.Response:
        with self._client() as client:
            return client.get("/api/grafico/categorias", params=params)

    def grafico_mensal(self, params: dict) -> httpx.Response:
        with self._client() as client:
            return client.get("/api/grafico/mensal", params=params)

    def grafico_evolucao(self, params: dict) -> httpx.Response:
        with self._client() as client:
            return client.get("/api/grafico/evolucao", params=params)

    def parcelas_ativas(self, params: dict) -> httpx.Response:
        with self._client() as client:
            return client.get("/api/parcelas-ativas", params=params)

    def excluir_grupo(self, grupo: str) -> httpx.Response:
        with self._client() as client:
            return client.delete(f"/api/grupos/{grupo}")

    def projecao(self, params: dict) -> httpx.Response:
        with self._client() as client:
            return client.get("/api/projecao", params=params)

    def listar_transacoes(self, params: dict) -> httpx.Response:
        with self._client() as client:
            return client.get("/api/transacoes", params=params)

    def criar_transacao(self, body: dict) -> httpx.Response:
        with self._client() as client:
            return client.post("/api/transacoes", json=body)

    def atualizar_transacao(self, id: int, body: dict) -> httpx.Response:
        with self._client() as client:
            return client.put(f"/api/transacoes/{id}", json=body)

    def excluir_transacao(self, id: int) -> httpx.Response:
        with self._client() as client:
            return client.delete(f"/api/transacoes/{id}")
