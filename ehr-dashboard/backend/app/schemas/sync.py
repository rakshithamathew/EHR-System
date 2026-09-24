from pydantic import BaseModel


class SyncResponse(BaseModel):
    source: str
    status: str
    patients_processed: int
    conditions_processed: int
    medications_processed: int
