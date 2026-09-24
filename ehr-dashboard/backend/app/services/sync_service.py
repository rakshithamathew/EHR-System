from app.repositories.patient_repository import PatientRepository
from app.repositories.sync_repository import SyncRepository


class SyncService:
    """EHR synchronization orchestration boundary."""

    def __init__(
        self,
        patient_repository: PatientRepository,
        sync_repository: SyncRepository,
    ) -> None:
        self.patient_repository = patient_repository
        self.sync_repository = sync_repository
