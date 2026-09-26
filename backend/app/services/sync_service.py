import asyncio
import logging
from typing import NotRequired, TypedDict
from uuid import UUID

import httpx

from app.connectors.base import FHIRConnector
from app.connectors.epic import (
    EpicAuthorizationRequiredError,
    EpicFHIRConnector,
)
from app.connectors.hapi import HAPIConnector
from app.connectors.oracle import OracleConnector
from app.core.config import settings
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
logger = logging.getLogger(__name__)


class SyncResult(TypedDict):
    source: str
    status: str
    patients_processed: int
    conditions_processed: int
    medications_processed: int
    error_message: NotRequired[str]


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
                    enabled=(
                        source.code in {"hapi", "oracle"}
                        or (
                            source.code == "epic"
                            and all(
                                (
                                    settings.epic_fhir_base_url,
                                    settings.epic_client_id,
                                    settings.epic_redirect_uri,
                                    settings.epic_authorization_url,
                                    settings.epic_token_url,
                                )
                            )
                        )
                    ),
                    last_sync=last_sync_response,
                )
            )

        return sources

    @staticmethod
    def _create_connector(
        source: EHRSource,
        *,
        access_token: str | None = None,
        epic_patient_id: str | None = None,
    ) -> FHIRConnector:
        connector_options = {
            "timeout": httpx.Timeout(15.0, connect=5.0),
            "max_attempts": 4,
        }
        if source.code == "hapi":
            return HAPIConnector(**connector_options)
        if source.code == "oracle":
            return OracleConnector(**connector_options)
        if source.code == "epic":
            if not access_token:
                raise EpicAuthorizationRequiredError(
                    "Epic authentication is required"
                )
            return EpicFHIRConnector(
                access_token=access_token,
                patient_id=epic_patient_id,
                **connector_options,
            )

        raise UnsupportedEHRSourceError(
            f"EHR source '{source.code}' is not supported"
        )

    async def _fetch_patient_resources(
        self,
        connector: FHIRConnector,
        patient_external_id: str,
        semaphore: asyncio.Semaphore,
    ) -> tuple[list[FHIRResource], list[FHIRResource]]:
        async def fetch(
            resource_type: str,
        ) -> list[FHIRResource]:
            try:
                async with semaphore:
                    if resource_type == "Condition":
                        return await connector.get_conditions(patient_external_id)
                    return await connector.get_medications(patient_external_id)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    raise EpicAuthorizationRequiredError(
                        "Epic access token is missing or expired"
                    ) from exc
                logger.warning(
                    "Skipping %s for patient %s after retries: %s",
                    resource_type,
                    patient_external_id,
                    exc,
                )
                return []
            except (httpx.HTTPError, ValueError) as exc:
                logger.warning(
                    "Skipping %s for patient %s after retries: %s",
                    resource_type,
                    patient_external_id,
                    exc,
                )
                return []

        conditions, medications = await asyncio.gather(
            fetch("Condition"),
            fetch("MedicationRequest"),
        )

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
        error_message: str | None = None,
    ) -> SyncResult:
        result: SyncResult = {
            "source": source_code,
            "status": status,
            "patients_processed": patients_processed,
            "conditions_processed": conditions_processed,
            "medications_processed": medications_processed,
        }
        if error_message:
            result["error_message"] = error_message
        return result

    async def sync_ehr(
        self,
        source_code: str,
        *,
        access_token: str | None = None,
        epic_patient_id: str | None = None,
    ) -> SyncResult:
        normalized_source_code = source_code.strip().lower()
        logger.info("Starting %s FHIR synchronization", normalized_source_code)
        source = self.sync_repository.get_ehr_source_by_code(normalized_source_code)
        if source is None:
            raise EHRSourceNotFoundError(
                f"EHR source '{normalized_source_code}' was not found"
            )

        connector = self._create_connector(
            source,
            access_token=access_token,
            epic_patient_id=epic_patient_id,
        )
        sync_run = self.sync_repository.create_sync_run(source.id)
        sync_run_id = sync_run.id
        self.sync_repository.commit()

        patients_processed = 0
        conditions_processed = 0
        medications_processed = 0

        try:
            async with connector:
                logger.info("Fetching %s Patient bundles", source.code)
                raw_patients = await connector.get_patients()
                logger.info(
                    "Fetched %d %s Patient resources",
                    len(raw_patients),
                    source.code,
                )
                persisted_patients: list[tuple[UUID, str]] = []
                seen_patient_ids: set[str] = set()

                for raw_patient in raw_patients:
                    patient = normalize_patient(raw_patient)
                    external_id = patient["external_id"]
                    if external_id is None:
                        raise ValueError("Patient resource is missing its external id")
                    if external_id in seen_patient_ids:
                        continue
                    seen_patient_ids.add(external_id)

                    persisted_patient = self.patient_repository.upsert_patient(
                        source.id,
                        patient,
                    )
                    persisted_patients.append((persisted_patient.id, external_id))
                    patients_processed += 1

                # A sync is a snapshot for one source. Remove rows left behind by
                # an earlier snapshot so a changing sandbox result cannot make the
                # patient directory grow every time sync is run.
                self.patient_repository.delete_patients_not_in(
                    source.id,
                    seen_patient_ids,
                )

                logger.info(
                    "Fetching Condition and MedicationRequest resources for %d patients",
                    len(persisted_patients),
                )
                related_resources = await self._fetch_all_patient_resources(
                    connector,
                    persisted_patients,
                )
                seen_condition_ids: set[str] = set()
                seen_medication_ids: set[str] = set()

                for (patient_id, _), (raw_conditions, raw_medications) in zip(
                    persisted_patients,
                    related_resources,
                    strict=True,
                ):
                    for raw_condition in raw_conditions:
                        condition = normalize_condition(raw_condition)
                        condition_id = condition["external_id"]
                        if condition_id is None:
                            raise ValueError(
                                "Condition resource is missing its external id"
                            )
                        if condition_id in seen_condition_ids:
                            continue
                        seen_condition_ids.add(condition_id)
                        self.patient_repository.upsert_condition(
                            source.id,
                            patient_id,
                            condition,
                        )
                        conditions_processed += 1

                    for raw_medication in raw_medications:
                        medication = normalize_medication_request(raw_medication)
                        medication_id = medication["external_id"]
                        if medication_id is None:
                            raise ValueError(
                                "MedicationRequest resource is missing its external id"
                            )
                        if medication_id in seen_medication_ids:
                            continue
                        seen_medication_ids.add(medication_id)
                        self.patient_repository.upsert_medication(
                            source.id,
                            patient_id,
                            medication,
                        )
                        medications_processed += 1

            self.sync_repository.mark_completed(
                sync_run_id,
                patients_processed=patients_processed,
                conditions_processed=conditions_processed,
                medications_processed=medications_processed,
            )
            self.sync_repository.commit()
            logger.info(
                "Completed %s sync: patients=%d conditions=%d medications=%d",
                source.code,
                patients_processed,
                conditions_processed,
                medications_processed,
            )
            return self._result(
                source.code,
                "completed",
                patients_processed,
                conditions_processed,
                medications_processed,
            )
        except EpicAuthorizationRequiredError as exc:
            logger.warning("Epic authorization expired during synchronization")
            self.sync_repository.rollback()
            self.sync_repository.mark_failed(
                sync_run_id,
                patients_processed=patients_processed,
                conditions_processed=conditions_processed,
                medications_processed=medications_processed,
                error_message=f"{type(exc).__name__}: {exc}",
            )
            self.sync_repository.commit()
            raise
        except httpx.HTTPStatusError as exc:
            if source.code == "epic" and exc.response.status_code == 401:
                self.sync_repository.rollback()
                self.sync_repository.mark_failed(
                    sync_run_id,
                    patients_processed=patients_processed,
                    conditions_processed=conditions_processed,
                    medications_processed=medications_processed,
                    error_message="Epic access token is missing or expired",
                )
                self.sync_repository.commit()
                raise EpicAuthorizationRequiredError(
                    "Epic access token is missing or expired"
                ) from exc
            logger.exception("%s FHIR synchronization failed", source.code)
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
                f"{source.name} sync failed: {exc}",
            )
        except Exception as exc:
            logger.exception("%s FHIR synchronization failed", source.code)
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
                f"{source.name} sync failed: {exc}",
            )
