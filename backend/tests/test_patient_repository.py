from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Condition, EHRSource, Medication, Patient
from app.routes import normalize_condition, normalize_medication, normalize_patient, upsert_clinical, upsert_patient


def source(session: Session, code: str) -> EHRSource:
    value = EHRSource(code=code, name=code.title(), base_url=f"https://{code}.test")
    session.add(value); session.flush(); return value


def test_patient_upsert_is_idempotent(db_session: Session) -> None:
    hapi_source = source(db_session, "hapi")
    upsert_patient(db_session, hapi_source.id, normalize_patient({"id": "123", "name": [{"text": "First"}]}))
    upsert_patient(db_session, hapi_source.id, normalize_patient({"id": "123", "name": [{"text": "Updated"}]}))
    assert db_session.scalar(select(func.count(Patient.id))) == 1
    assert db_session.scalar(select(Patient)).name == "Updated"


def test_patient_identity_is_source_scoped(db_session: Session) -> None:
    data = normalize_patient({"id": "123", "name": [{"text": "Shared"}]})
    upsert_patient(db_session, source(db_session, "hapi").id, data)
    upsert_patient(db_session, source(db_session, "oracle").id, data)
    assert db_session.scalar(select(func.count(Patient.id))) == 2


def test_clinical_upserts_are_idempotent(db_session: Session) -> None:
    hapi_source = source(db_session, "hapi"); patient = upsert_patient(db_session, hapi_source.id, normalize_patient({"id": "p1"}))
    condition = normalize_condition({"id": "c1", "code": {"coding": [{"display": "Condition"}]}})
    medication = normalize_medication({"id": "m1", "medicationCodeableConcept": {"coding": [{"display": "Medicine"}]}})
    upsert_clinical(db_session, Condition, "uq_conditions_ehr_source_external_id", hapi_source.id, patient.id, condition)
    upsert_clinical(db_session, Condition, "uq_conditions_ehr_source_external_id", hapi_source.id, patient.id, condition)
    upsert_clinical(db_session, Medication, "uq_medications_ehr_source_external_id", hapi_source.id, patient.id, medication)
    upsert_clinical(db_session, Medication, "uq_medications_ehr_source_external_id", hapi_source.id, patient.id, medication)
    assert db_session.scalar(select(func.count(Condition.id))) == 1
    assert db_session.scalar(select(func.count(Medication.id))) == 1
