from pydantic_settings import BaseSettings, SettingsConfigDict

CATEGORIAS = (
    "ALIMENTACAO",
    "TRANSPORTE",
    "LAZER",
    "EDUCACAO",
    "GASTOS_FIXOS",
    "COMPRAS",
    "GASTOS_PONTUAIS",
    "INVESTIMENTO",
    "RECEITA",
)

TIPOS = (
    "GASTO",
    "INVESTIMENTO",
    "RECEITA",
)

PERIODOS = {
    "mes_atual": "Mês atual",
    "mes_anterior": "Mês anterior",
    "ultimos_3_meses": "Últimos 3 meses",
    "ultimos_6_meses": "Últimos 6 meses",
    "ano_atual": "Ano atual",
    "tudo": "Tudo",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    backend_url: str = "http://localhost:8000"
    frontend_port: int = 5000
    backend_timeout: float = 10.0
