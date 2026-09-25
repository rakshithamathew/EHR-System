from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    test_database_url: str | None = None
    frontend_url: str | None = None
    hapi_fhir_base_url: str | None = None
    oracle_fhir_base_url: str | None = None
    epic_fhir_base_url: str | None = None
    epic_client_id: str | None = None
    epic_redirect_uri: str | None = None
    epic_authorization_url: str | None = None
    epic_token_url: str | None = None

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        """Use the installed Psycopg 3 driver for provider-supplied URLs."""
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
