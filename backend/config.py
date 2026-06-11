from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ACCESS_EXPIRES_MIN: int = 30
    JWT_REFRESH_EXPIRES_DAYS: int = 7
    ADMIN_EMAILS_RAW: str = Field(default="", alias="ADMIN_EMAILS")

    @cached_property
    def ADMIN_EMAILS(self) -> set[str]:
        return {
            parte.strip().lower()
            for parte in self.ADMIN_EMAILS_RAW.split(",")
            if parte.strip()
        }


settings = Settings()
