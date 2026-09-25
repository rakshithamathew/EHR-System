from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.patient_repository import PatientRepository
from app.repositories.sync_repository import SyncRepository
from app.schemas.ehr import EHRSourceResponse, SourceResponse
from app.schemas.sync import DatabaseSyncResponse, SyncResponse
from app.services.sync_service import (
    EHRSourceNotFoundError,
    EpicAuthorizationRequiredError,
    SyncService,
    UnsupportedEHRSourceError,
)
from app.services.epic_auth_service import EPIC_SESSION_COOKIE, epic_oauth_store

router = APIRouter(prefix="/ehrs")
public_router = APIRouter()


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


@public_router.get("/sources", response_model=list[SourceResponse])
def list_sources(
    service: Annotated[SyncService, Depends(get_sync_service)],
) -> list[SourceResponse]:
    return [
        SourceResponse(
            id=source.code,
            label=source.name,
            enabled=source.enabled,
            last_sync=source.last_sync,
        )
        for source in service.list_ehr_sources()
    ]


@public_router.post("/sync", response_model=DatabaseSyncResponse)
async def sync_source(
    request: Request,
    source: Annotated[str, Query()],
    service: Annotated[SyncService, Depends(get_sync_service)],
) -> DatabaseSyncResponse | JSONResponse:
    normalized_source = source.strip().lower()
    if normalized_source not in {"hapi", "oracle", "epic"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported EHR source '{normalized_source}'",
        )

    try:
        if normalized_source == "epic":
            token = epic_oauth_store.get_token(
                request.cookies.get(EPIC_SESSION_COOKIE)
            )
            if token is None:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "error": "epic_auth_required",
                        "detail": "Epic token expired, please log in again",
                    },
                )
            result = await service.sync_ehr(
                normalized_source,
                access_token=token.value,
                epic_patient_id=token.patient_id,
            )
        else:
            result = await service.sync_ehr(normalized_source)
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
    except EpicAuthorizationRequiredError:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "epic_auth_required",
                "detail": "Epic token expired, please log in again",
            },
        )

    if result["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.get("error_message")
            or f"{normalized_source.title()} synchronization failed",
        )

    patients = result["patients_processed"]
    conditions = result["conditions_processed"]
    medications = result["medications_processed"]
    return DatabaseSyncResponse(
        synced=patients + conditions + medications,
        patients=patients,
        conditions=conditions,
        medications=medications,
    )
