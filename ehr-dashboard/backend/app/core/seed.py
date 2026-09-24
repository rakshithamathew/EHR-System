from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_session_factory
from app.models.ehr_source import EHRSource


def seed_ehr_sources(session: Session) -> None:
    """Create or refresh the configured EHR sources without duplicates."""

    statement = insert(EHRSource).values(
        [
            {
                "code": "hapi",
                "name": "HAPI FHIR",
                "base_url": settings.hapi_fhir_base_url or "",
            },
            {
                "code": "oracle",
                "name": "Oracle Health",
                "base_url": settings.oracle_fhir_base_url or "",
            },
            {
                "code": "epic",
                "name": "Epic",
                "base_url": settings.epic_fhir_base_url or "",
            },
        ]
    )
    statement = statement.on_conflict_do_update(
        constraint="uq_ehr_sources_code",
        set_={
            "name": statement.excluded.name,
            "base_url": statement.excluded.base_url,
        },
    )
    session.execute(statement)


def seed_configured_ehr_sources() -> None:
    """Seed sources in their own transaction for startup or CLI use."""

    with get_session_factory()() as session:
        seed_ehr_sources(session)
        session.commit()


if __name__ == "__main__":
    seed_configured_ehr_sources()
