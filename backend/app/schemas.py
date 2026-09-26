from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class LastSync(BaseModel):
    status: str
    started_at: datetime
    completed_at: datetime | None
    patients_processed: int
    conditions_processed: int
    medications_processed: int
    error_message: str | None


class SourceOut(BaseModel):
    id: str
    label: str
    enabled: bool
    last_sync: LastSync | None = None


class SyncOut(BaseModel):
    synced: int
    patients: int
    conditions: int
    medications: int


class PatientOut(BaseModel):
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


class PatientPage(BaseModel):
    items: list[PatientOut]
    page: int
    page_size: int
    total: int
    has_next: bool


class ConditionOut(BaseModel):
    id: UUID | str
    external_id: str
    clinical_status: str | None
    verification_status: str | None
    code: str | None
    code_system: str | None
    display: str | None
    onset_date: date | None


class MedicationOut(BaseModel):
    id: UUID | str
    external_id: str
    status: str | None
    medication_code: str | None
    medication_display: str | None
    authored_on: datetime | None


class PatientDetails(BaseModel):
    patient: PatientOut
    conditions: list[ConditionOut]
    medications: list[MedicationOut]
