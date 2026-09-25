from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ehr_source import EHRSource
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.utils.fhir import normalize_patient


def add_source(session: Session, code: str, name: str) -> EHRSource:
    source = EHRSource(
        code=code,
        name=name,
        base_url=f"https://{code}.example/fhir",
    )
    session.add(source)
    session.flush()
    return source


def patient_resource(name: str) -> dict[str, object]:
    return {
        "resourceType": "Patient",
        "id": "123",
        "name": [{"text": name}],
    }


def test_patient_upsert_is_idempotent(db_session: Session) -> None:
    hapi = add_source(db_session, "hapi", "HAPI FHIR")
    repository = PatientRepository(db_session)

    repository.upsert_patient(
        hapi.id,
        normalize_patient(patient_resource("First Name")),
    )
    repository.upsert_patient(
        hapi.id,
        normalize_patient(patient_resource("Updated Name")),
    )
    db_session.flush()

    patient_count = db_session.scalar(
        select(func.count(Patient.id)).where(
            Patient.ehr_source_id == hapi.id,
            Patient.external_id == "123",
        )
    )
    stored_patient = db_session.scalar(
        select(Patient).where(
            Patient.ehr_source_id == hapi.id,
            Patient.external_id == "123",
        )
    )

    assert patient_count == 1
    assert stored_patient is not None
    assert stored_patient.name == "Updated Name"


def test_patient_identity_is_scoped_to_ehr_source(db_session: Session) -> None:
    hapi = add_source(db_session, "hapi", "HAPI FHIR")
    oracle = add_source(db_session, "oracle", "Oracle Health")
    repository = PatientRepository(db_session)
    patient = normalize_patient(patient_resource("Shared Identifier"))

    repository.upsert_patient(hapi.id, patient)
    repository.upsert_patient(oracle.id, patient)
    db_session.flush()

    stored_patients = list(
        db_session.scalars(
            select(Patient)
            .where(Patient.external_id == "123")
            .order_by(Patient.ehr_source_id)
        )
    )

    assert len(stored_patients) == 2
    assert {patient.ehr_source_id for patient in stored_patients} == {
        hapi.id,
        oracle.id,
    }
