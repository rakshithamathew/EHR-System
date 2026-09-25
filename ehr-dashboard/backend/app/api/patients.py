from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientDetailsResponse, PatientSummaryResponse
from app.services.patient_service import PatientNotFoundError, PatientService

router = APIRouter(prefix="/patients")


def get_patient_service(
    session: Annotated[Session, Depends(get_db)],
) -> PatientService:
    return PatientService(PatientRepository(session))


@router.get("", response_model=list[PatientSummaryResponse])
def list_patients(
    service: Annotated[PatientService, Depends(get_patient_service)],
    source: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PatientSummaryResponse]:
    return service.list_patients(
        source=source,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/{patient_id}", response_model=PatientDetailsResponse)
def get_patient_details(
    patient_id: UUID,
    service: Annotated[PatientService, Depends(get_patient_service)],
) -> PatientDetailsResponse:
    try:
        return service.get_patient_details(patient_id)
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
