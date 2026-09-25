from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_session_factory
from app.repositories.sync_repository import SyncRepository


def seed_ehr_sources(session: Session) -> None:
    """Create or refresh the configured EHR sources without duplicates."""

    SyncRepository(session).upsert_ehr_sources(
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


def seed_configured_ehr_sources() -> None:
    """Seed sources in their own transaction for startup or CLI use."""

    with get_session_factory()() as session:
        seed_ehr_sources(session)
        session.commit()


if __name__ == "__main__":
    seed_configured_ehr_sources()
