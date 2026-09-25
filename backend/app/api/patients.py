from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.patient_repository import PatientRepository
from app.schemas.patient import PatientDetailsResponse, PatientPageResponse
from app.services.epic_auth_service import EPIC_SESSION_COOKIE, epic_oauth_store
from app.services.patient_service import PatientNotFoundError, PatientService

router = APIRouter(prefix="/patients")
SYNC_SOURCES = frozenset({"hapi", "oracle", "epic"})


def get_patient_service(
    session: Annotated[Session, Depends(get_db)],
) -> PatientService:
    return PatientService(PatientRepository(session))


def _supported_source(source: str) -> str:
    normalized = source.strip().lower()
    if normalized not in SYNC_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported patient source '{normalized}'",
        )
    return normalized


def _epic_auth_required(request: Request, source: str) -> bool:
    return source == "epic" and epic_oauth_store.get_token(
        request.cookies.get(EPIC_SESSION_COOKIE)
    ) is None


@router.get("", response_model=PatientPageResponse)
def list_patients(
    request: Request,
    service: Annotated[PatientService, Depends(get_patient_service)],
    source: Annotated[str, Query()],
    page: Annotated[int, Query(ge=1)] = 1,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    sort_by: Annotated[
        Literal["name", "external_id", "birth_date", "gender"],
        Query(),
    ] = "name",
    sort_order: Annotated[Literal["asc", "desc"], Query()] = "asc",
) -> PatientPageResponse | JSONResponse:
    """Return already-synchronized patients from PostgreSQL."""

    normalized_source = _supported_source(source)
    if _epic_auth_required(request, normalized_source):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "epic_auth_required",
                "detail": "Epic token expired, please log in again",
            },
        )

    return service.list_patient_page(
        source=normalized_source,
        search=search,
        limit=limit,
        page=page,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{patient_id}", response_model=PatientDetailsResponse)
def get_patient_details(
    request: Request,
    patient_id: UUID,
    service: Annotated[PatientService, Depends(get_patient_service)],
    source: Annotated[str | None, Query()] = None,
) -> PatientDetailsResponse | JSONResponse:
    normalized_source = _supported_source(source) if source is not None else None
    if normalized_source and _epic_auth_required(request, normalized_source):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "epic_auth_required",
                "detail": "Epic token expired, please log in again",
            },
        )
    try:
        return service.get_patient_details(
            patient_id,
            source=normalized_source,
        )
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
