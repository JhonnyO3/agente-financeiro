from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    OPENAI_API_KEY: str
    EVOLUTION_API_URL: str
    EVOLUTION_INSTANCE: str
    EVOLUTION_API_KEY: str
    WHATSAPP_ALLOWED_NUMBER: str
    AGENTE_USUARIO_EMAIL: str = "jhonatas2004@gmail.com"


settings = Settings()
