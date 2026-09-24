from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str | None = None
    frontend_url: str = "http://localhost:5173"
    hapi_fhir_base_url: str = "https://hapi.fhir.org/baseR4"
    oracle_fhir_base_url: str = (
        "https://fhir-open.cerner.com/r4/"
        "ec2458f2-1e24-41c8-b71b-0e701af7583d"
    )
    epic_fhir_base_url: str | None = None
    epic_client_id: str | None = None
    epic_redirect_uri: str | None = None
    epic_authorization_url: str | None = None
    epic_token_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
