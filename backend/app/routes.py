import asyncio
from collections.abc import Mapping
from datetime import date, datetime, timezone
from typing import Annotated, Any, Literal
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import get_db, settings
from app.ehr import epic, hapi, oracle
from app.models import Condition, EHRSource, Medication, Patient, SyncRun
from app.schemas import ConditionOut, LastSync, MedicationOut, PatientDetails, PatientOut, PatientPage, SourceOut, SyncOut

router = APIRouter(prefix="/api")
SUPPORTED = {"hapi", "oracle", "epic"}


def text(value: Any) -> str | None:
    return (value.strip() or None) if isinstance(value, str) else None


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def first(value: Any) -> Mapping[str, Any]:
    return next((item for item in value if isinstance(item, Mapping)), {}) if isinstance(value, list) else {}


def coding(value: Any) -> Mapping[str, Any]:
    return first(mapping(value).get("coding"))


def concept_code(value: Any) -> str | None:
    concept = mapping(value)
    return text(coding(concept).get("code")) or text(concept.get("text"))


def fhir_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def fhir_datetime(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None
    except ValueError:
        return None


def normalize_patient(resource: Mapping[str, Any]) -> dict[str, Any]:
    name = first(resource.get("name"))
    given = [item.strip() for item in name.get("given", []) if isinstance(item, str) and item.strip()]
    family = text(name.get("family"))
    return {"external_id": text(resource.get("id")), "name": text(name.get("text")) or " ".join([*given, *([family] if family else [])]) or None, "given_name": given[0] if given else None, "family_name": family, "gender": text(resource.get("gender")), "birth_date": fhir_date(resource.get("birthDate")), "raw_resource": dict(resource)}


def normalize_condition(resource: Mapping[str, Any]) -> dict[str, Any]:
    code = mapping(resource.get("code")); item = coding(code)
    onset = resource.get("onsetDateTime") or mapping(resource.get("onsetPeriod")).get("start")
    parsed_datetime = fhir_datetime(onset)
    return {"external_id": text(resource.get("id")), "clinical_status": concept_code(resource.get("clinicalStatus")), "verification_status": concept_code(resource.get("verificationStatus")), "code": text(item.get("code")), "code_system": text(item.get("system")), "display": text(item.get("display")) or text(code.get("text")), "onset_date": fhir_date(onset) or (parsed_datetime.date() if parsed_datetime else None), "raw_resource": dict(resource)}


def normalize_medication(resource: Mapping[str, Any]) -> dict[str, Any]:
    concept = mapping(resource.get("medicationCodeableConcept")); item = coding(concept); reference = mapping(resource.get("medicationReference"))
    return {"external_id": text(resource.get("id")), "status": text(resource.get("status")), "medication_code": text(item.get("code")) or text(reference.get("reference")), "medication_display": text(item.get("display")) or text(concept.get("text")) or text(reference.get("display")), "authored_on": fhir_datetime(resource.get("authoredOn")), "raw_resource": dict(resource)}


def seed_sources(session: Session) -> None:
    rows = [{"code": "hapi", "name": "HAPI FHIR", "base_url": settings.hapi_fhir_base_url or ""}, {"code": "oracle", "name": "Oracle Health", "base_url": settings.oracle_fhir_base_url or ""}, {"code": "epic", "name": "Epic", "base_url": settings.epic_fhir_base_url or ""}]
    statement = insert(EHRSource).values(rows)
    session.execute(statement.on_conflict_do_update(constraint="uq_ehr_sources_code", set_={"name": statement.excluded.name, "base_url": statement.excluded.base_url})); session.commit()


def upsert_patient(session: Session, source_id: int, data: dict[str, Any]) -> Patient:
    statement = insert(Patient).values(ehr_source_id=source_id, last_synced_at=func.now(), **data)
    updates = {key: getattr(statement.excluded, key) for key in ("name", "given_name", "family_name", "gender", "birth_date", "raw_resource")}
    statement = statement.on_conflict_do_update(constraint="uq_patients_ehr_source_external_id", set_=updates | {"last_synced_at": func.now(), "updated_at": func.now()}).returning(Patient)
    return session.execute(statement, execution_options={"populate_existing": True}).scalar_one()


def upsert_clinical(session: Session, model: type[Condition] | type[Medication], constraint: str, source_id: int, patient_id: UUID, data: dict[str, Any]) -> None:
    statement = insert(model).values(ehr_source_id=source_id, patient_id=patient_id, **data)
    updates = {key: getattr(statement.excluded, key) for key in data if key != "external_id"}
    session.execute(statement.on_conflict_do_update(constraint=constraint, set_=updates | {"patient_id": statement.excluded.patient_id, "updated_at": func.now()}))


async def sync_source(session: Session, source: EHRSource, token: epic.AccessToken | None = None) -> dict[str, int]:
    if not source.base_url: raise HTTPException(503, f"{source.code.upper()} FHIR base URL is not configured")
    run = SyncRun(ehr_source_id=source.id, status="running"); session.add(run); session.commit()
    counts = {"patients": 0, "conditions": 0, "medications": 0}; client = hapi.FHIRClient(source.base_url, token.value if token else None)
    try:
        provider = {"hapi": hapi, "oracle": oracle, "epic": epic}[source.code]
        raw_patients = await (epic.fetch_patients(client, token.patient_id) if source.code == "epic" and token else provider.fetch_patients(client))
        patients: list[tuple[UUID, str]] = []; seen: set[str] = set()
        for raw in raw_patients:
            data = normalize_patient(raw); external_id = data["external_id"]
            if raw.get("resourceType") != "Patient" or not external_id or external_id in seen: continue
            seen.add(external_id); stored = upsert_patient(session, source.id, data); patients.append((stored.id, external_id)); counts["patients"] += 1
        statement = delete(Patient).where(Patient.ehr_source_id == source.id)
        if seen: statement = statement.where(Patient.external_id.not_in(seen))
        session.execute(statement)
        semaphore = asyncio.Semaphore(5)
        async def related(patient_id: str):
            async def fetch(fetcher):
                try:
                    async with semaphore:
                        return await fetcher(client, patient_id)
                except httpx.HTTPStatusError as error:
                    if source.code == "epic" and error.response.status_code == 401:
                        raise
                    return []
                except (httpx.HTTPError, ValueError):
                    return []
            return await asyncio.gather(fetch(provider.fetch_conditions), fetch(provider.fetch_medications))
        results = await asyncio.gather(*(related(external_id) for _, external_id in patients))
        seen_conditions: set[str] = set(); seen_medications: set[str] = set()
        for (patient_id, _), (conditions, medications) in zip(patients, results, strict=True):
            for raw in conditions:
                data = normalize_condition(raw); external_id = data["external_id"]
                if raw.get("resourceType") == "Condition" and external_id and external_id not in seen_conditions:
                    seen_conditions.add(external_id); upsert_clinical(session, Condition, "uq_conditions_ehr_source_external_id", source.id, patient_id, data); counts["conditions"] += 1
            for raw in medications:
                data = normalize_medication(raw); external_id = data["external_id"]
                if raw.get("resourceType") == "MedicationRequest" and external_id and external_id not in seen_medications:
                    seen_medications.add(external_id); upsert_clinical(session, Medication, "uq_medications_ehr_source_external_id", source.id, patient_id, data); counts["medications"] += 1
        session.execute(update(SyncRun).where(SyncRun.id == run.id).values(status="completed", completed_at=datetime.now(timezone.utc), patients_processed=counts["patients"], conditions_processed=counts["conditions"], medications_processed=counts["medications"])); session.commit(); return counts
    except Exception as error:
        session.rollback(); session.execute(update(SyncRun).where(SyncRun.id == run.id).values(status="failed", completed_at=datetime.now(timezone.utc), error_message=f"{type(error).__name__}: {error}")); session.commit(); raise
    finally: await client.close()


def source_or_400(source: str) -> str:
    value = source.strip().lower()
    if value not in SUPPORTED: raise HTTPException(400, f"Unsupported EHR source '{value}'")
    return value


@router.get("/health")
def health(): return {"status": "ok"}


@router.get("/sources", response_model=list[SourceOut])
def sources(session: Annotated[Session, Depends(get_db)]):
    result = []
    for source in session.scalars(select(EHRSource).order_by(EHRSource.id)):
        run = session.scalar(select(SyncRun).where(SyncRun.ehr_source_id == source.id, SyncRun.status == "completed").order_by(SyncRun.started_at.desc()).limit(1))
        enabled = bool(source.base_url) and (source.code != "epic" or all((settings.epic_client_id, settings.epic_redirect_uri, settings.epic_authorization_url, settings.epic_token_url)))
        result.append(SourceOut(id=source.code, label=source.name, enabled=enabled, last_sync=LastSync.model_validate(run, from_attributes=True) if run else None))
    return result


@router.get("/ehrs")
def ehr_sources(session: Annotated[Session, Depends(get_db)]):
    """Backward-compatible form of /sources used by earlier clients."""
    return [{"code": item.id, "name": item.label, "enabled": item.enabled, "last_sync": item.last_sync} for item in sources(session)]


@router.post("/sync", response_model=SyncOut)
async def sync(request: Request, source: str, session: Annotated[Session, Depends(get_db)]):
    code = source_or_400(source); token = epic.get_token(request.cookies.get(epic.SESSION_COOKIE)) if code == "epic" else None
    if code == "epic" and not token: return JSONResponse(status_code=401, content={"error": "epic_auth_required", "detail": "Epic token expired, please log in again"})
    row = session.scalar(select(EHRSource).where(EHRSource.code == code))
    if not row: raise HTTPException(404, f"EHR source '{code}' was not found")
    try: counts = await sync_source(session, row, token)
    except httpx.HTTPError as error: raise HTTPException(502, f"{code.title()} synchronization failed: {error}") from error
    return SyncOut(synced=sum(counts.values()), **counts)


@router.post("/ehrs/{source}/sync")
async def sync_ehr(source: str, request: Request, session: Annotated[Session, Depends(get_db)]):
    result = await sync(request, source, session)
    if isinstance(result, JSONResponse):
        return result
    return {"source": source_or_400(source), "status": "completed", "patients_processed": result.patients, "conditions_processed": result.conditions, "medications_processed": result.medications}


def patient_out(patient: Patient, source: str, conditions: int = 0, medications: int = 0) -> PatientOut:
    return PatientOut(id=patient.id, source=source, external_id=patient.external_id, name=patient.name, given_name=patient.given_name, family_name=patient.family_name, gender=patient.gender, birth_date=patient.birth_date, condition_count=conditions, medication_count=medications, last_synced_at=patient.last_synced_at)


@router.get("/patients", response_model=PatientPage)
def patients(request: Request, source: str, session: Annotated[Session, Depends(get_db)], page: int = Query(1, ge=1), search: str | None = None, limit: int = Query(10, ge=1, le=100), sort_by: Literal["name", "external_id", "birth_date", "gender"] = "name", sort_order: Literal["asc", "desc"] = "asc"):
    code = source_or_400(source); term = search.strip() if search and search.strip() else None
    if code == "epic" and not epic.get_token(request.cookies.get(epic.SESSION_COOKIE)):
        return JSONResponse(status_code=401, content={"error": "epic_auth_required", "detail": "Epic token expired, please log in again"})
    condition_counts = select(Condition.patient_id, func.count(Condition.id).label("count")).group_by(Condition.patient_id).subquery(); medication_counts = select(Medication.patient_id, func.count(Medication.id).label("count")).group_by(Medication.patient_id).subquery()
    filters = [EHRSource.code == code]
    if term:
        pattern = f"%{term}%"; filters.append(or_(Patient.external_id.ilike(pattern), Patient.name.ilike(pattern), Patient.given_name.ilike(pattern), Patient.family_name.ilike(pattern)))
    total = session.scalar(select(func.count(Patient.id)).join(EHRSource).where(*filters)) or 0
    column = {"name": Patient.name, "external_id": Patient.external_id, "birth_date": Patient.birth_date, "gender": Patient.gender}[sort_by]; order = column.desc().nulls_last() if sort_order == "desc" else column.asc().nulls_last()
    query = select(Patient, EHRSource.code, func.coalesce(condition_counts.c.count, 0), func.coalesce(medication_counts.c.count, 0)).join(EHRSource).outerjoin(condition_counts, condition_counts.c.patient_id == Patient.id).outerjoin(medication_counts, medication_counts.c.patient_id == Patient.id).where(*filters).order_by(order, Patient.id).limit(limit).offset((page - 1) * limit)
    return PatientPage(items=[patient_out(*row) for row in session.execute(query)], page=page, page_size=limit, total=total, has_next=page * limit < total)


@router.get("/patients/{patient_id}", response_model=PatientDetails)
def patient_details(request: Request, patient_id: UUID, session: Annotated[Session, Depends(get_db)], source: str | None = None):
    if source and source_or_400(source) == "epic" and not epic.get_token(request.cookies.get(epic.SESSION_COOKIE)):
        return JSONResponse(status_code=401, content={"error": "epic_auth_required", "detail": "Epic token expired, please log in again"})
    query = select(Patient, EHRSource.code).join(EHRSource).where(Patient.id == patient_id)
    if source: query = query.where(EHRSource.code == source_or_400(source))
    row = session.execute(query).one_or_none()
    if not row: raise HTTPException(404, f"Patient '{patient_id}' was not found")
    conditions = list(session.scalars(select(Condition).where(Condition.patient_id == patient_id).order_by(Condition.created_at, Condition.id))); medications = list(session.scalars(select(Medication).where(Medication.patient_id == patient_id).order_by(Medication.created_at, Medication.id)))
    return PatientDetails(patient=patient_out(row[0], row[1], len(conditions), len(medications)), conditions=[ConditionOut.model_validate(item, from_attributes=True) for item in conditions], medications=[MedicationOut.model_validate(item, from_attributes=True) for item in medications])


def required(value: str | None, name: str) -> str:
    if not value or not value.strip(): raise HTTPException(503, f"{name} is not configured")
    return value.strip()


@router.get("/epic/login")
def epic_login():
    state, challenge = epic.begin_authorization(); query = urlencode({"response_type": "code", "client_id": required(settings.epic_client_id, "EPIC_CLIENT_ID"), "redirect_uri": required(settings.epic_redirect_uri, "EPIC_REDIRECT_URI"), "scope": epic.SCOPES, "state": state, "code_challenge": challenge, "code_challenge_method": "S256", "aud": required(settings.epic_fhir_base_url, "EPIC_FHIR_BASE_URL")})
    return RedirectResponse(f"{required(settings.epic_authorization_url, 'EPIC_AUTHORIZATION_URL')}?{query}")


@router.get("/epic/callback")
async def epic_callback(code: str | None = None, state: str | None = None, error: str | None = None, error_description: str | None = None):
    if error:
        raise HTTPException(400, error_description or error)
    if not code or not state:
        raise HTTPException(400, "Epic callback requires code and state")
    pending = epic.consume_authorization(state)
    if not pending: raise HTTPException(400, "Epic OAuth state is invalid or expired")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(required(settings.epic_token_url, "EPIC_TOKEN_URL"), data={"grant_type": "authorization_code", "code": code, "redirect_uri": required(settings.epic_redirect_uri, "EPIC_REDIRECT_URI"), "client_id": required(settings.epic_client_id, "EPIC_CLIENT_ID"), "code_verifier": pending.verifier}); response.raise_for_status(); payload = response.json()
    epic.save_token(pending.session_id, payload["access_token"], int(payload.get("expires_in", 300)), payload.get("patient")); result = RedirectResponse(f"{required(settings.frontend_url, 'FRONTEND_URL').rstrip('/')}/dashboard?source=epic&epic=connected"); secure = required(settings.epic_redirect_uri, "EPIC_REDIRECT_URI").startswith("https://"); result.set_cookie(epic.SESSION_COOKIE, pending.session_id, httponly=True, secure=secure, samesite="none" if secure else "lax", max_age=int(payload.get("expires_in", 300))); return result


@router.get("/epic/status")
def epic_status(request: Request): return {"connected": epic.get_token(request.cookies.get(epic.SESSION_COOKIE)) is not None}


@router.post("/epic/logout")
def epic_logout(request: Request):
    epic.revoke_token(request.cookies.get(epic.SESSION_COOKIE)); response = JSONResponse({"connected": False}); response.delete_cookie(epic.SESSION_COOKIE); return response
