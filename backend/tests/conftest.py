import os
from collections.abc import Generator
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401
from app.database import Base, settings


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide an isolated PostgreSQL schema that is rolled back after a test."""

    database_url = (
        os.getenv("TEST_DATABASE_URL")
        or settings.test_database_url
        or settings.database_url
    )
    if not database_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required")
    if not database_url.startswith("postgresql"):
        pytest.skip("Persistence tests require PostgreSQL")

    engine = create_engine(database_url, poolclass=NullPool)
    try:
        connection = engine.connect()
    except OperationalError as exc:
        engine.dispose()
        pytest.skip(f"PostgreSQL is unavailable: {exc}")

    transaction = connection.begin()
    schema_name = f"test_{uuid4().hex}"
    session = Session(bind=connection, expire_on_commit=False)

    try:
        connection.exec_driver_sql(f'CREATE SCHEMA "{schema_name}"')
        connection.exec_driver_sql(
            f'SET LOCAL search_path TO "{schema_name}"'
        )
        Base.metadata.create_all(connection)
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
