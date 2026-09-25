from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FHIRPatientResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str | None
    gender: str | None
    birth_date: date | None = Field(alias="birthDate")


class FHIRPatientPageResponse(BaseModel):
    items: list[FHIRPatientResponse]
    page: int
    has_next: bool


class PatientSummaryResponse(BaseModel):
    id: UUID | str
    source: str
    external_id: str
    name: str | None
    given_name: str | None
    family_name: str | None
    gender: str | None
    birth_date: date | None
    condition_count: int = 0
    medication_count: int = 0
    last_synced_at: datetime | None = None


class PatientPageResponse(BaseModel):
    items: list[PatientSummaryResponse]
    page: int
    has_next: bool


class ConditionResponse(BaseModel):
    id: UUID | str
    external_id: str
    clinical_status: str | None
    verification_status: str | None
    code: str | None
    code_system: str | None
    display: str | None
    onset_date: date | None


class MedicationResponse(BaseModel):
    id: UUID | str
    external_id: str
    status: str | None
    medication_code: str | None
    medication_display: str | None
    authored_on: datetime | None


class PatientDetailsResponse(BaseModel):
    patient: PatientSummaryResponse
    conditions: list[ConditionResponse]
    medications: list[MedicationResponse]
