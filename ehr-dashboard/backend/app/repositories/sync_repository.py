from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.ehr_source import EHRSource
from app.models.sync_run import SyncRun


class SyncRepository:
    """Sync run query and persistence boundary."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_ehr_source_by_code(self, source_code: str) -> EHRSource | None:
        statement = select(EHRSource).where(EHRSource.code == source_code)
        return self.session.execute(statement).scalar_one_or_none()

    def upsert_ehr_sources(self, sources: list[dict[str, str]]) -> None:
        statement = insert(EHRSource).values(sources)
        statement = statement.on_conflict_do_update(
            constraint="uq_ehr_sources_code",
            set_={
                "name": statement.excluded.name,
                "base_url": statement.excluded.base_url,
            },
        )
        self.session.execute(statement)

    def list_ehr_sources_with_latest_sync(
        self,
    ) -> list[tuple[EHRSource, SyncRun | None]]:
        latest_sync_id = (
            select(SyncRun.id)
            .where(SyncRun.ehr_source_id == EHRSource.id)
            .order_by(SyncRun.started_at.desc(), SyncRun.id.desc())
            .limit(1)
            .correlate(EHRSource)
            .scalar_subquery()
        )
        statement = (
            select(EHRSource, SyncRun)
            .outerjoin(SyncRun, SyncRun.id == latest_sync_id)
            .order_by(EHRSource.id)
        )
        return [tuple(row) for row in self.session.execute(statement).all()]

    def create_sync_run(self, ehr_source_id: int) -> SyncRun:
        sync_run = SyncRun(
            ehr_source_id=ehr_source_id,
            status="running",
            patients_processed=0,
            conditions_processed=0,
            medications_processed=0,
        )
        self.session.add(sync_run)
        self.session.flush()
        return sync_run

    def mark_completed(
        self,
        sync_run_id: UUID,
        *,
        patients_processed: int,
        conditions_processed: int,
        medications_processed: int,
    ) -> None:
        statement = (
            update(SyncRun)
            .where(SyncRun.id == sync_run_id)
            .values(
                status="completed",
                completed_at=datetime.now(timezone.utc),
                patients_processed=patients_processed,
                conditions_processed=conditions_processed,
                medications_processed=medications_processed,
                error_message=None,
            )
        )
        self.session.execute(statement)

    def mark_failed(
        self,
        sync_run_id: UUID,
        *,
        patients_processed: int,
        conditions_processed: int,
        medications_processed: int,
        error_message: str,
    ) -> None:
        statement = (
            update(SyncRun)
            .where(SyncRun.id == sync_run_id)
            .values(
                status="failed",
                completed_at=datetime.now(timezone.utc),
                patients_processed=patients_processed,
                conditions_processed=conditions_processed,
                medications_processed=medications_processed,
                error_message=error_message,
            )
        )
        self.session.execute(statement)

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
