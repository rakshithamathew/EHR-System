import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.ehr.hapi import FHIRClient, FHIRResource, fetch_conditions, fetch_medications, fetch_patient

SESSION_COOKIE = "epic_session"
SCOPES = "openid fhirUser patient/Patient.read patient/Condition.read patient/MedicationRequest.read"
AUTHORIZATION_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize"
TOKEN_URL = "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token"
FHIR_AUDIENCE = "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4"


@dataclass(frozen=True)
class PendingAuthorization:
    session_id: str
    verifier: str
    expires_at: datetime


@dataclass(frozen=True)
class AccessToken:
    value: str
    expires_at: datetime
    patient_id: str | None = None


pending: dict[str, PendingAuthorization] = {}
tokens: dict[str, AccessToken] = {}


def begin_authorization() -> tuple[str, str]:
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    pending[state] = PendingAuthorization(secrets.token_urlsafe(32), verifier, datetime.now(timezone.utc) + timedelta(minutes=10))
    return state, challenge


def consume_authorization(state: str) -> PendingAuthorization | None:
    value = pending.pop(state, None)
    return value if value and value.expires_at > datetime.now(timezone.utc) else None


def save_token(session_id: str, value: str, expires_in: int, patient_id: str | None) -> None:
    tokens[session_id] = AccessToken(value, datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 30, 0)), patient_id)


def get_token(session_id: str | None) -> AccessToken | None:
    token = tokens.get(session_id or "")
    if token and token.expires_at > datetime.now(timezone.utc):
        return token
    if session_id:
        tokens.pop(session_id, None)
    return None


def revoke_token(session_id: str | None) -> None:
    if session_id:
        tokens.pop(session_id, None)


async def fetch_patients(client: FHIRClient, patient_id: str | None) -> list[FHIRResource]:
    return [await fetch_patient(client, patient_id)] if patient_id else await client.all("Patient", {"_count": 5})


__all__ = ["FHIRClient", "fetch_patients", "fetch_conditions", "fetch_medications"]
