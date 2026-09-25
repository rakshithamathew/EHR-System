from pydantic import BaseModel


class SyncResponse(BaseModel):
    source: str
    status: str
    patients_processed: int
    conditions_processed: int
    medications_processed: int


class DatabaseSyncResponse(BaseModel):
    synced: int
    patients: int
    conditions: int
    medications: int
