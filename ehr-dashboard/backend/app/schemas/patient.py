from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class PatientSummaryResponse(BaseModel):
    id: UUID
    source: str
    external_id: str
    name: str | None
    given_name: str | None
    family_name: str | None
    gender: str | None
    birth_date: date | None


class ConditionResponse(BaseModel):
    id: UUID
    external_id: str
    clinical_status: str | None
    verification_status: str | None
    code: str | None
    code_system: str | None
    display: str | None
    onset_date: date | None


class MedicationResponse(BaseModel):
    id: UUID
    external_id: str
    status: str | None
    medication_code: str | None
    medication_display: str | None
    authored_on: datetime | None


class PatientDetailsResponse(BaseModel):
    patient: PatientSummaryResponse
    conditions: list[ConditionResponse]
    medications: list[MedicationResponse]
