import asyncio
import logging
from collections.abc import Awaitable
from uuid import UUID

import httpx

from app.connectors.base import FHIRConnector
from app.connectors.epic import EpicFHIRConnector
from app.connectors.hapi import HAPIConnector
from app.connectors.oracle import OracleConnector
from app.models.condition import Condition
from app.models.medication import Medication
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import (
    ConditionResponse,
    FHIRPatientPageResponse,
    FHIRPatientResponse,
    MedicationResponse,
    PatientDetailsResponse,
    PatientPageResponse,
    PatientSummaryResponse,
)
from app.utils.fhir import (
    FHIRResource,
    normalize_condition,
    normalize_medication_request,
    normalize_patient,
)


class PatientSourceFetchError(RuntimeError):
    """Raised when a remote patient source cannot be read."""


class PatientNotFoundError(LookupError):
    """Raised when a patient ID does not exist."""


logger = logging.getLogger(__name__)


async def _optional_clinical_resources(
    request: Awaitable[list[FHIRResource]],
    *,
    source: str,
    resource_type: str,
) -> list[FHIRResource]:
    """Keep slow sandbox clinical searches from hiding patient demographics."""

    try:
        return await asyncio.wait_for(request, timeout=12.0)
    except (TimeoutError, httpx.HTTPError, ValueError) as exc:
        logger.warning(
            "%s %s lookup failed: %s",
            source,
            resource_type,
            exc,
        )
        return []


def _provider_connector(
    source: str,
    *,
    access_token: str | None = None,
) -> FHIRConnector:
    connector_options = {
        "timeout": httpx.Timeout(12.0, connect=3.0),
        "max_attempts": 2,
    }
    if source == "hapi":
        return HAPIConnector(**connector_options)
    if source == "oracle":
        return OracleConnector(**connector_options)
    if source == "epic":
        return EpicFHIRConnector(access_token=access_token, **connector_options)
    raise ValueError(f"Unsupported EHR source '{source}'")


def _fhir_patient_response(resource: FHIRResource) -> FHIRPatientResponse | None:
    patient = normalize_patient(resource)
    external_id = patient["external_id"]
    if external_id is None:
        return None
    return FHIRPatientResponse(
        id=external_id,
        name=patient["name"],
        gender=patient["gender"],
        birth_date=patient["birth_date"],
    )


def _source_error(source: str, exc: Exception) -> PatientSourceFetchError:
    detail = str(exc).strip() or "the provider closed the connection"
    return PatientSourceFetchError(
        f"{source.title()} FHIR request failed ({type(exc).__name__}): {detail}"
    )


async def fetch_patient_page(
    *,
    source: str,
    page: int,
    count: int,
    search: str | None = None,
    access_token: str | None = None,
) -> FHIRPatientPageResponse:
    connector = _provider_connector(source, access_token=access_token)
    try:
        async with connector:
            result = await connector.get_patient_page(
                page=page,
                count=count,
                search=search,
            )
    except httpx.HTTPStatusError as exc:
        if source == "epic" and exc.response.status_code == 401:
            raise EpicAuthorizationRequiredError(
                "Epic access token is missing or expired"
            ) from exc
        raise _source_error(source, exc) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise _source_error(source, exc) from exc

    patients = [
        patient
        for resource in result["resources"]
        if (patient := _fhir_patient_response(resource)) is not None
    ]
    return FHIRPatientPageResponse(
        items=patients,
        page=page,
        has_next=result["has_next"],
    )


async def fetch_fhir_patient_details(
    *,
    source: str,
    patient_id: str,
    access_token: str | None = None,
) -> PatientDetailsResponse:
    connector = _provider_connector(source, access_token=access_token)
    try:
        async with connector:
            raw_patient, raw_conditions, raw_medications = await asyncio.gather(
                connector.get_patient(patient_id),
                _optional_clinical_resources(
                    connector.get_conditions(patient_id),
                    source=source,
                    resource_type="Condition",
                ),
                _optional_clinical_resources(
                    connector.get_medications(patient_id),
                    source=source,
                    resource_type="MedicationRequest",
                ),
            )
    except httpx.HTTPStatusError as exc:
        if source == "epic" and exc.response.status_code == 401:
            raise EpicAuthorizationRequiredError(
                "Epic access token is missing or expired"
            ) from exc
        if exc.response.status_code == 404:
            raise PatientNotFoundError(
                f"{source.title()} patient '{patient_id}' was not found"
            ) from exc
        raise _source_error(source, exc) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise _source_error(source, exc) from exc

    patient = normalize_patient(raw_patient)
    external_id = patient["external_id"] or patient_id

    conditions: list[ConditionResponse] = []
    for resource in raw_conditions:
        condition = normalize_condition(resource)
        condition_id = condition["external_id"]
        if condition_id is None:
            continue
        conditions.append(
            ConditionResponse(
                id=condition_id,
                external_id=condition_id,
                clinical_status=condition["clinical_status"],
                verification_status=condition["verification_status"],
                code=condition["code"],
                code_system=condition["code_system"],
                display=condition["display"],
                onset_date=condition["onset_date"],
            )
        )

    medications: list[MedicationResponse] = []
    for resource in raw_medications:
        medication = normalize_medication_request(resource)
        medication_id = medication["external_id"]
        if medication_id is None:
            continue
        medications.append(
            MedicationResponse(
                id=medication_id,
                external_id=medication_id,
                status=medication["status"],
                medication_code=medication["medication_code"],
                medication_display=medication["medication_display"],
                authored_on=medication["authored_on"],
            )
        )

    return PatientDetailsResponse(
        patient=PatientSummaryResponse(
            id=external_id,
            source=source,
            external_id=external_id,
            name=patient["name"],
            given_name=patient["given_name"],
            family_name=patient["family_name"],
            gender=patient["gender"],
            birth_date=patient["birth_date"],
        ),
        conditions=conditions,
        medications=medications,
    )


class PatientService:
    def __init__(self, repository: PatientRepository) -> None:
        self.repository = repository

    @staticmethod
    def _patient_summary(
        patient: Patient,
        source: str,
        condition_count: int = 0,
        medication_count: int = 0,
    ) -> PatientSummaryResponse:
        return PatientSummaryResponse(
            id=patient.id,
            source=source,
            external_id=patient.external_id,
            name=patient.name,
            given_name=patient.given_name,
            family_name=patient.family_name,
            gender=patient.gender,
            birth_date=patient.birth_date,
            condition_count=condition_count,
            medication_count=medication_count,
            last_synced_at=patient.last_synced_at,
        )

    @staticmethod
    def _condition(condition: Condition) -> ConditionResponse:
        return ConditionResponse(
            id=condition.id,
            external_id=condition.external_id,
            clinical_status=condition.clinical_status,
            verification_status=condition.verification_status,
            code=condition.code,
            code_system=condition.code_system,
            display=condition.display,
            onset_date=condition.onset_date,
        )

    @staticmethod
    def _medication(medication: Medication) -> MedicationResponse:
        return MedicationResponse(
            id=medication.id,
            external_id=medication.external_id,
            status=medication.status,
            medication_code=medication.medication_code,
            medication_display=medication.medication_display,
            authored_on=medication.authored_on,
        )

    def list_patients(
        self,
        *,
        source: str | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> list[PatientSummaryResponse]:
        source_code = source.strip().lower() if source and source.strip() else None
        search_term = search.strip() if search and search.strip() else None
        rows = self.repository.list_patients(
            source_code=source_code,
            search=search_term,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return [
            self._patient_summary(
                patient,
                code,
                condition_count,
                medication_count,
            )
            for patient, code, condition_count, medication_count in rows
        ]

    def list_patient_page(
        self,
        *,
        source: str,
        search: str | None,
        limit: int,
        page: int,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> PatientPageResponse:
        rows = self.list_patients(
            source=source,
            search=search,
            limit=limit + 1,
            offset=(page - 1) * limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PatientPageResponse(
            items=rows[:limit],
            page=page,
            has_next=len(rows) > limit,
        )

    def get_patient_details(
        self,
        patient_id: UUID,
        *,
        source: str | None = None,
    ) -> PatientDetailsResponse:
        details = self.repository.get_patient_details(patient_id)
        if details is None:
            raise PatientNotFoundError(f"Patient '{patient_id}' was not found")

        patient, stored_source, conditions, medications = details
        if source is not None and source != stored_source:
            raise PatientNotFoundError(f"Patient '{patient_id}' was not found")

        return PatientDetailsResponse(
            patient=self._patient_summary(
                patient,
                stored_source,
                len(conditions),
                len(medications),
            ),
            conditions=[self._condition(condition) for condition in conditions],
            medications=[self._medication(medication) for medication in medications],
        )
