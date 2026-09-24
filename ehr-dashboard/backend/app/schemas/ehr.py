from datetime import datetime

from pydantic import BaseModel


class LastSyncResponse(BaseModel):
    status: str
    started_at: datetime
    completed_at: datetime | None
    patients_processed: int
    conditions_processed: int
    medications_processed: int
    error_message: str | None


class EHRSourceResponse(BaseModel):
    code: str
    name: str
    enabled: bool
    last_sync: LastSyncResponse | None = None
