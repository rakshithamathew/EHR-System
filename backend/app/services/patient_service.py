from uuid import UUID

from app.models.condition import Condition
from app.models.medication import Medication
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import (
    ConditionResponse,
    MedicationResponse,
    PatientDetailsResponse,
    PatientPageResponse,
    PatientSummaryResponse,
)


class PatientNotFoundError(LookupError):
    """Raised when a patient ID does not exist."""


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
        source_code = source.strip().lower()
        search_term = search.strip() if search and search.strip() else None
        total = self.repository.count_patients(
            source_code=source_code,
            search=search_term,
        )
        rows = self.list_patients(
            source=source_code,
            search=search_term,
            limit=limit,
            offset=(page - 1) * limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return PatientPageResponse(
            items=rows,
            page=page,
            page_size=limit,
            total=total,
            has_next=page * limit < total,
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
