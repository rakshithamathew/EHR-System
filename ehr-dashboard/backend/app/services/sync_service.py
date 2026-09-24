import asyncio
from typing import TypedDict
from uuid import UUID

from app.connectors.base import FHIRConnector
from app.connectors.hapi import HAPIConnector
from app.connectors.oracle import OracleConnector
from app.models.ehr_source import EHRSource
from app.repositories.patient_repository import PatientRepository
from app.repositories.sync_repository import SyncRepository
from app.schemas.ehr import EHRSourceResponse, LastSyncResponse
from app.utils.fhir import (
    FHIRResource,
    normalize_condition,
    normalize_medication_request,
    normalize_patient,
)

MAX_CONCURRENT_PATIENT_REQUESTS = 5


class SyncResult(TypedDict):
    source: str
    status: str
    patients_processed: int
    conditions_processed: int
    medications_processed: int


class EHRSourceNotFoundError(LookupError):
    """Raised when a configured EHR source cannot be found."""


class UnsupportedEHRSourceError(ValueError):
    """Raised when synchronization is unavailable for a source code."""


class SyncService:
    """EHR synchronization orchestration boundary."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        sync_repository: SyncRepository,
        *,
        max_concurrent_patient_requests: int = MAX_CONCURRENT_PATIENT_REQUESTS,
    ) -> None:
        if max_concurrent_patient_requests < 1:
            raise ValueError("max_concurrent_patient_requests must be at least 1")

        self.patient_repository = patient_repository
        self.sync_repository = sync_repository
        self.max_concurrent_patient_requests = max_concurrent_patient_requests

    def list_ehr_sources(self) -> list[EHRSourceResponse]:
        sources: list[EHRSourceResponse] = []
        for source, last_sync in self.sync_repository.list_ehr_sources_with_latest_sync():
            last_sync_response = (
                LastSyncResponse(
                    status=last_sync.status,
                    started_at=last_sync.started_at,
                    completed_at=last_sync.completed_at,
                    patients_processed=last_sync.patients_processed,
                    conditions_processed=last_sync.conditions_processed,
                    medications_processed=last_sync.medications_processed,
                    error_message=last_sync.error_message,
                )
                if last_sync is not None
                else None
            )
            sources.append(
                EHRSourceResponse(
                    code=source.code,
                    name=source.name,
                    enabled=source.code in {"hapi", "oracle"},
                    last_sync=last_sync_response,
                )
            )

        return sources

    @staticmethod
    def _create_connector(source: EHRSource) -> FHIRConnector:
        if source.code == "hapi":
            return HAPIConnector()
        if source.code == "oracle":
            return OracleConnector()

        raise UnsupportedEHRSourceError(
            f"EHR source '{source.code}' is not supported"
        )

    async def _fetch_patient_resources(
        self,
        connector: FHIRConnector,
        patient_external_id: str,
        semaphore: asyncio.Semaphore,
    ) -> tuple[list[FHIRResource], list[FHIRResource]]:
        async with semaphore:
            conditions = await connector.get_conditions(patient_external_id)

        async with semaphore:
            medications = await connector.get_medications(patient_external_id)

        return conditions, medications

    async def _fetch_all_patient_resources(
        self,
        connector: FHIRConnector,
        patients: list[tuple[UUID, str]],
    ) -> list[tuple[list[FHIRResource], list[FHIRResource]]]:
        semaphore = asyncio.Semaphore(self.max_concurrent_patient_requests)
        tasks = [
            asyncio.create_task(
                self._fetch_patient_resources(
                    connector,
                    external_id,
                    semaphore,
                )
            )
            for _, external_id in patients
        ]

        try:
            return await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

    @staticmethod
    def _result(
        source_code: str,
        status: str,
        patients_processed: int,
        conditions_processed: int,
        medications_processed: int,
    ) -> SyncResult:
        return {
            "source": source_code,
            "status": status,
            "patients_processed": patients_processed,
            "conditions_processed": conditions_processed,
            "medications_processed": medications_processed,
        }

    async def sync_ehr(self, source_code: str) -> SyncResult:
        normalized_source_code = source_code.strip().lower()
        source = self.sync_repository.get_ehr_source_by_code(normalized_source_code)
        if source is None:
            raise EHRSourceNotFoundError(
                f"EHR source '{normalized_source_code}' was not found"
            )

        connector = self._create_connector(source)
        sync_run = self.sync_repository.create_sync_run(source.id)
        sync_run_id = sync_run.id
        self.sync_repository.commit()

        patients_processed = 0
        conditions_processed = 0
        medications_processed = 0

        try:
            async with connector:
                raw_patients = await connector.get_patients()
                persisted_patients: list[tuple[UUID, str]] = []

                for raw_patient in raw_patients:
                    patient = normalize_patient(raw_patient)
                    external_id = patient["external_id"]
                    if external_id is None:
                        raise ValueError("Patient resource is missing its external id")

                    persisted_patient = self.patient_repository.upsert_patient(
                        source.id,
                        patient,
                    )
                    persisted_patients.append((persisted_patient.id, external_id))
                    patients_processed += 1

                related_resources = await self._fetch_all_patient_resources(
                    connector,
                    persisted_patients,
                )

                for (patient_id, _), (raw_conditions, raw_medications) in zip(
                    persisted_patients,
                    related_resources,
                    strict=True,
                ):
                    for raw_condition in raw_conditions:
                        self.patient_repository.upsert_condition(
                            source.id,
                            patient_id,
                            normalize_condition(raw_condition),
                        )
                        conditions_processed += 1

                    for raw_medication in raw_medications:
                        self.patient_repository.upsert_medication(
                            source.id,
                            patient_id,
                            normalize_medication_request(raw_medication),
                        )
                        medications_processed += 1

            self.sync_repository.mark_completed(
                sync_run_id,
                patients_processed=patients_processed,
                conditions_processed=conditions_processed,
                medications_processed=medications_processed,
            )
            self.sync_repository.commit()
            return self._result(
                source.code,
                "completed",
                patients_processed,
                conditions_processed,
                medications_processed,
            )
        except Exception as exc:
            self.sync_repository.rollback()
            self.sync_repository.mark_failed(
                sync_run_id,
                patients_processed=patients_processed,
                conditions_processed=conditions_processed,
                medications_processed=medications_processed,
                error_message=f"{type(exc).__name__}: {exc}",
            )
            self.sync_repository.commit()
            return self._result(
                source.code,
                "failed",
                patients_processed,
                conditions_processed,
                medications_processed,
            )
