from collections.abc import Generator
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


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
        if isinstance(value, str):
            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+psycopg://", 1)
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL must be configured")
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with get_session_factory()() as session:
        yield session
