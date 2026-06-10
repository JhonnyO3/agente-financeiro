from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    OPENAI_API_KEY: str
    EVOLUTION_API_URL: str
    EVOLUTION_INSTANCE: str
    EVOLUTION_API_KEY: str
    WHATSAPP_ALLOWED_NUMBER: str

    class Config:
        env_file = ".env"


settings = Settings()
