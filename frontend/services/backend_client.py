import httpx

from frontend.services import sessao


class BackendClient:
    def __init__(self, base_url: str, timeout: float = 10.0):
        self._base_url = base_url
        self._timeout = timeout

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self._base_url, timeout=self._timeout)

    def login(self, email: str, senha: str) -> httpx.Response:
        with self._client() as client:
            return client.request(
                "POST", "/auth/login", json={"email": email, "senha": senha}
            )

    def logout(self, refresh_token: str) -> httpx.Response:
        with self._client() as client:
            return client.request(
                "POST", "/auth/logout", json={"refresh_token": refresh_token}
            )

    def _refresh(self, client: httpx.Client, refresh_token: str) -> httpx.Response:
        return client.request(
            "POST", "/auth/refresh", json={"refresh_token": refresh_token}
        )

    def _autenticado(self, method: str, url: str, **kwargs) -> httpx.Response:
        with self._client() as client:
            resposta = self._enviar(client, method, url, **kwargs)
            if resposta.status_code != 401:
                return resposta

            refresh = sessao.refresh_token()
            if not refresh:
                sessao.limpar()
                return resposta

            renovacao = self._refresh(client, refresh)
            if renovacao.status_code != 200:
                sessao.limpar()
                return resposta

            novos = renovacao.json()
            sessao.atualizar_tokens(novos["access_token"], novos["refresh_token"])

            refeita = self._enviar(client, method, url, **kwargs)
            if refeita.status_code == 401:
                sessao.limpar()
            return refeita

    def _enviar(
        self, client: httpx.Client, method: str, url: str, **kwargs
    ) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}) or {})
        token = sessao.access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return client.request(method, url, headers=headers, **kwargs)

    def resumo(self, params: dict) -> httpx.Response:
        return self._autenticado("GET", "/api/resumo", params=params)

    def grafico_categorias(self, params: dict) -> httpx.Response:
        return self._autenticado("GET", "/api/grafico/categorias", params=params)

    def grafico_mensal(self, params: dict) -> httpx.Response:
        return self._autenticado("GET", "/api/grafico/mensal", params=params)

    def grafico_evolucao(self, params: dict) -> httpx.Response:
        return self._autenticado("GET", "/api/grafico/evolucao", params=params)

    def parcelas_ativas(self, params: dict) -> httpx.Response:
        return self._autenticado("GET", "/api/parcelas-ativas", params=params)

    def excluir_grupo(self, grupo: str) -> httpx.Response:
        return self._autenticado("DELETE", f"/api/grupos/{grupo}")

    def projecao(self, params: dict) -> httpx.Response:
        return self._autenticado("GET", "/api/projecao", params=params)

    def listar_transacoes(self, params: dict) -> httpx.Response:
        return self._autenticado("GET", "/api/transacoes", params=params)

    def criar_transacao(self, body: dict) -> httpx.Response:
        return self._autenticado("POST", "/api/transacoes", json=body)

    def atualizar_transacao(self, id: int, body: dict) -> httpx.Response:
        return self._autenticado("PUT", f"/api/transacoes/{id}", json=body)

    def excluir_transacao(self, id: int) -> httpx.Response:
        return self._autenticado("DELETE", f"/api/transacoes/{id}")

    def atualizar_grupo(self, grupo: str, body: dict) -> httpx.Response:
        return self._autenticado("PUT", f"/api/grupos/{grupo}", json=body)

    def criar_grupo(self, body: dict) -> httpx.Response:
        return self._autenticado("POST", "/api/grupos", json=body)

    def listar_gastos_fixos(self) -> httpx.Response:
        return self._autenticado("GET", "/api/gastos-fixos")

    def criar_gasto_fixo(self, body: dict) -> httpx.Response:
        return self._autenticado("POST", "/api/gastos-fixos", json=body)

    def atualizar_gasto_fixo(self, id: int, body: dict) -> httpx.Response:
        return self._autenticado("PUT", f"/api/gastos-fixos/{id}", json=body)

    def excluir_gasto_fixo(self, id: int) -> httpx.Response:
        return self._autenticado("DELETE", f"/api/gastos-fixos/{id}")
