from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.patient_repository import PatientRepository
from app.repositories.sync_repository import SyncRepository
from app.schemas.ehr import EHRSourceResponse
from app.schemas.sync import SyncResponse
from app.services.sync_service import (
    EHRSourceNotFoundError,
    SyncService,
    UnsupportedEHRSourceError,
)

router = APIRouter(prefix="/ehrs")


def get_sync_service(
    session: Annotated[Session, Depends(get_db)],
) -> SyncService:
    return SyncService(
        patient_repository=PatientRepository(session),
        sync_repository=SyncRepository(session),
    )


@router.get("", response_model=list[EHRSourceResponse])
def list_ehr_sources(
    service: Annotated[SyncService, Depends(get_sync_service)],
) -> list[EHRSourceResponse]:
    return service.list_ehr_sources()


@router.post("/{source}/sync", response_model=SyncResponse)
async def sync_ehr_source(
    source: str,
    service: Annotated[SyncService, Depends(get_sync_service)],
) -> SyncResponse:
    try:
        result = await service.sync_ehr(source)
    except EHRSourceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except UnsupportedEHRSourceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SyncResponse(**result)
