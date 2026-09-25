from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.services.epic_auth_service import EPIC_SESSION_COOKIE, epic_oauth_store

router = APIRouter(prefix="/epic")

EPIC_SCOPES = (
    "patient/Patient.read "
    "patient/Condition.read "
    "patient/MedicationRequest.read"
)
EPIC_CLIENT_ID = "6b14ff08-2522-41fa-9c83-0b395a36add4"
EPIC_REDIRECT_URI = "http://localhost:5173/callback"
EPIC_AUTHORIZATION_URL = (
    "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
)
EPIC_TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
EPIC_FHIR_AUDIENCE = (
    "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"
)


def _required_setting(value: str | None, name: str) -> str:
    if value is None or not value.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{name} is not configured",
        )
    return value.strip()


def _exact_setting(value: str | None, name: str, expected: str) -> str:
    configured = _required_setting(value, name)
    if configured != expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{name} must exactly equal {expected}",
        )
    return configured


@router.get("/status")
async def epic_status(request: Request) -> dict[str, bool]:
    token = epic_oauth_store.get_token(request.cookies.get(EPIC_SESSION_COOKIE))
    return {"connected": token is not None}


@router.get("/login")
async def epic_login() -> RedirectResponse:
    authorization_url = _exact_setting(
        settings.epic_authorization_url,
        "EPIC_AUTHORIZATION_URL",
        EPIC_AUTHORIZATION_URL,
    )
    client_id = _exact_setting(
        settings.epic_client_id,
        "EPIC_CLIENT_ID",
        EPIC_CLIENT_ID,
    )
    redirect_uri = _exact_setting(
        settings.epic_redirect_uri,
        "EPIC_REDIRECT_URI",
        EPIC_REDIRECT_URI,
    )
    _exact_setting(
        settings.epic_fhir_base_url,
        "EPIC_FHIR_BASE_URL",
        EPIC_FHIR_AUDIENCE,
    )

    state, _, _, code_challenge = epic_oauth_store.begin_authorization()
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": EPIC_SCOPES,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "aud": EPIC_FHIR_AUDIENCE,
        }
    )
    redirect_url = f"{authorization_url}?{query}"
    print(f"Epic authorization URL: {redirect_url}", flush=True)
    return RedirectResponse(redirect_url, status_code=302)


@router.get("/callback")
async def epic_callback(
    code: str | None = Query(default=None),
    state_value: str | None = Query(default=None, alias="state"),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    if error:
        detail = error_description or error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    if not code or not state_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Epic callback requires code and state",
        )

    pending = epic_oauth_store.consume_authorization(state_value)
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Epic OAuth state is invalid or expired",
        )

    token_url = _exact_setting(
        settings.epic_token_url,
        "EPIC_TOKEN_URL",
        EPIC_TOKEN_URL,
    )
    client_id = _exact_setting(
        settings.epic_client_id,
        "EPIC_CLIENT_ID",
        EPIC_CLIENT_ID,
    )
    redirect_uri = _exact_setting(
        settings.epic_redirect_uri,
        "EPIC_REDIRECT_URI",
        EPIC_REDIRECT_URI,
    )
    print("Epic token exchange started", flush=True)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            token_response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "code_verifier": pending.code_verifier,
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            payload = token_response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Epic token exchange failed ({type(exc).__name__})",
        ) from exc

    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Epic token response did not include an access_token",
        )

    expires_in = payload.get("expires_in", 300)
    try:
        expires_in_seconds = int(expires_in)
    except (TypeError, ValueError):
        expires_in_seconds = 300
    epic_oauth_store.save_token(
        pending.session_id,
        access_token,
        expires_in=expires_in_seconds,
        patient_id=payload.get("patient") if isinstance(payload.get("patient"), str) else None,
        scope=payload.get("scope") if isinstance(payload.get("scope"), str) else None,
    )
    print(
        "Epic token exchange succeeded "
        f"(expires_in={expires_in_seconds}, patient_context={bool(payload.get('patient'))})",
        flush=True,
    )

    frontend_url = _required_setting(settings.frontend_url, "FRONTEND_URL").rstrip("/")
    response = RedirectResponse(
        f"{frontend_url}/dashboard?source=epic&epic=connected",
        status_code=302,
    )
    response.set_cookie(
        EPIC_SESSION_COOKIE,
        pending.session_id,
        httponly=True,
        secure=redirect_uri.lower().startswith("https://"),
        samesite="lax",
        max_age=expires_in_seconds,
        path="/",
    )
    return response
