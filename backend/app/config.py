from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./hyrox_coach.db"
    anthropic_api_key: str | None = None
    terra_api_key: str | None = None
    terra_dev_id: str | None = None
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"


settings = Settings()
