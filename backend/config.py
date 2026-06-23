from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ACCESS_EXPIRES_MIN: int = 30
    JWT_REFRESH_EXPIRES_DAYS: int = 7
    ADMIN_EMAILS_RAW: str = Field(alias="ADMIN_EMAILS")
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174"

    @property
    def ADMIN_EMAILS(self) -> set[str]:
        return {
            parte.strip().lower()
            for parte in self.ADMIN_EMAILS_RAW.split(",")
            if parte.strip()
        }

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
