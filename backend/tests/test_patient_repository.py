from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ehr_source import EHRSource
from app.models.condition import Condition
from app.models.medication import Medication
from app.models.patient import Patient
from app.repositories.patient_repository import PatientRepository
from app.services.patient_service import PatientService
from app.utils.fhir import (
    normalize_condition,
    normalize_medication_request,
    normalize_patient,
)


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


def test_sync_snapshot_removes_only_stale_patients_for_its_source(
    db_session: Session,
) -> None:
    hapi = add_source(db_session, "hapi", "HAPI FHIR")
    oracle = add_source(db_session, "oracle", "Oracle Health")
    repository = PatientRepository(db_session)

    repository.upsert_patient(hapi.id, normalize_patient(patient_resource("Current")))
    stale = patient_resource("Stale")
    stale["id"] = "stale"
    repository.upsert_patient(hapi.id, normalize_patient(stale))
    repository.upsert_patient(oracle.id, normalize_patient(stale))

    assert repository.delete_patients_not_in(hapi.id, {"123"}) == 1
    db_session.flush()

    remaining = list(db_session.scalars(select(Patient).order_by(Patient.ehr_source_id)))
    assert [(row.ehr_source_id, row.external_id) for row in remaining] == [
        (hapi.id, "123"),
        (oracle.id, "stale"),
    ]


def test_clinical_resources_upsert_and_patient_counts(db_session: Session) -> None:
    hapi = add_source(db_session, "hapi", "HAPI FHIR")
    repository = PatientRepository(db_session)
    patient = repository.upsert_patient(
        hapi.id,
        normalize_patient(patient_resource("Clinical Patient")),
    )

    first_condition = {
        "resourceType": "Condition",
        "id": "condition-1",
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "code": {"coding": [{"code": "123", "display": "First"}]},
    }
    updated_condition = {
        **first_condition,
        "code": {"coding": [{"code": "123", "display": "Updated"}]},
    }
    medication = {
        "resourceType": "MedicationRequest",
        "id": "medication-1",
        "status": "active",
        "medicationCodeableConcept": {
            "coding": [{"code": "456", "display": "Example medication"}]
        },
    }

    repository.upsert_condition(
        hapi.id,
        patient.id,
        normalize_condition(first_condition),
    )
    repository.upsert_condition(
        hapi.id,
        patient.id,
        normalize_condition(updated_condition),
    )
    repository.upsert_medication(
        hapi.id,
        patient.id,
        normalize_medication_request(medication),
    )
    repository.upsert_medication(
        hapi.id,
        patient.id,
        normalize_medication_request(medication),
    )
    db_session.flush()

    assert db_session.scalar(select(func.count(Condition.id))) == 1
    assert db_session.scalar(select(func.count(Medication.id))) == 1
    stored_condition = db_session.scalar(select(Condition))
    assert stored_condition is not None
    assert stored_condition.display == "Updated"

    rows = repository.list_patients(
        source_code="hapi",
        search=None,
        limit=20,
        offset=0,
    )
    assert len(rows) == 1
    assert rows[0][2:] == (1, 1)


def test_patient_list_applies_server_side_sorting(db_session: Session) -> None:
    hapi = add_source(db_session, "hapi", "HAPI FHIR")
    repository = PatientRepository(db_session)
    repository.upsert_patient(
        hapi.id,
        normalize_patient(
            {
                "resourceType": "Patient",
                "id": "older",
                "name": [{"text": "Older Patient"}],
                "birthDate": "1970-01-01",
            }
        ),
    )
    repository.upsert_patient(
        hapi.id,
        normalize_patient(
            {
                "resourceType": "Patient",
                "id": "younger",
                "name": [{"text": "Younger Patient"}],
                "birthDate": "2000-01-01",
            }
        ),
    )
    db_session.flush()

    rows = repository.list_patients(
        source_code="hapi",
        search=None,
        limit=20,
        offset=0,
        sort_by="birth_date",
        sort_order="desc",
    )

    assert [patient.external_id for patient, *_ in rows] == ["younger", "older"]
    assert repository.count_patients(source_code="hapi", search=None) == 2
    assert repository.count_patients(source_code="hapi", search="Older") == 1
    assert repository.count_patients(source_code="oracle", search=None) == 0

    page = PatientService(repository).list_patient_page(
        source="hapi",
        search=None,
        limit=1,
        page=1,
        sort_by="birth_date",
        sort_order="desc",
    )
    assert page.total == 2
    assert page.page_size == 1
    assert page.has_next is True
    assert [patient.external_id for patient in page.items] == ["younger"]
