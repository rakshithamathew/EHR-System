from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from app.connectors.epic import EpicAuthorizationRequiredError
from app.schemas.patient import PatientDetailsResponse, PatientPageResponse
from app.services.epic_auth_service import EPIC_SESSION_COOKIE, epic_oauth_store
from app.services.patient_service import (
    PatientNotFoundError,
    PatientSourceFetchError,
    fetch_fhir_patient_details,
    fetch_patient_page,
)

router = APIRouter(prefix="/patients")


def _epic_access_token(request: Request, source: str) -> str | None:
    if source != "epic":
        return None
    token = epic_oauth_store.get_token(request.cookies.get(EPIC_SESSION_COOKIE))
    if token is None:
        return None
    return token.value


@router.get("", response_model=PatientPageResponse)
async def list_patients(
    request: Request,
    source: Annotated[str, Query()],
    page: Annotated[int, Query(ge=1)] = 1,
    search: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PatientPageResponse | JSONResponse:
    normalized_source = source.strip().lower()
    normalized_search = search.strip() if search and search.strip() else None
    access_token = _epic_access_token(request, normalized_source)
    if normalized_source == "epic" and access_token is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "epic_auth_required"},
        )

    try:
        return await fetch_patient_page(
            source=normalized_source,
            page=page,
            count=limit,
            search=normalized_search,
            access_token=access_token,
        )
    except EpicAuthorizationRequiredError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "epic_auth_required"},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PatientSourceFetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc


@router.get("/{patient_id}", response_model=PatientDetailsResponse)
async def get_patient_details(
    request: Request,
    patient_id: str,
    source: Annotated[str, Query()],
) -> PatientDetailsResponse | JSONResponse:
    normalized_source = source.strip().lower()
    access_token = _epic_access_token(request, normalized_source)
    if normalized_source == "epic" and access_token is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "epic_auth_required"},
        )
    try:
        return await fetch_fhir_patient_details(
            source=normalized_source,
            patient_id=patient_id,
            access_token=access_token,
        )
    except EpicAuthorizationRequiredError as exc:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "epic_auth_required"},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except PatientNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except PatientSourceFetchError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
