from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.condition import Condition
from app.models.ehr_source import EHRSource
from app.models.medication import Medication
from app.models.patient import Patient
from app.utils.fhir import (
    NormalizedCondition,
    NormalizedMedicationRequest,
    NormalizedPatient,
)


class PatientRepository:
    """Persistence boundary for patients and their clinical resources."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _require_external_id(external_id: str | None, resource_type: str) -> str:
        if external_id is None:
            raise ValueError(f"{resource_type} resource is missing its external id")

        return external_id

    def upsert_patient(
        self,
        ehr_source_id: int,
        patient: NormalizedPatient,
    ) -> Patient:
        """Insert a patient or update it using its source-scoped identity."""

        external_id = self._require_external_id(patient["external_id"], "Patient")
        statement = insert(Patient).values(
            ehr_source_id=ehr_source_id,
            external_id=external_id,
            name=patient["name"],
            given_name=patient["given_name"],
            family_name=patient["family_name"],
            gender=patient["gender"],
            birth_date=patient["birth_date"],
            raw_resource=patient["raw_resource"],
            last_synced_at=func.now(),
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_patients_ehr_source_external_id",
            set_={
                "name": statement.excluded.name,
                "given_name": statement.excluded.given_name,
                "family_name": statement.excluded.family_name,
                "gender": statement.excluded.gender,
                "birth_date": statement.excluded.birth_date,
                "raw_resource": statement.excluded.raw_resource,
                "last_synced_at": func.now(),
                "updated_at": func.now(),
            },
        ).returning(Patient)

        result = self.session.execute(
            statement,
            execution_options={"populate_existing": True},
        )
        return result.scalar_one()

    def upsert_condition(
        self,
        ehr_source_id: int,
        patient_id: UUID,
        condition: NormalizedCondition,
    ) -> Condition:
        """Insert a condition or update it using its source-scoped identity."""

        external_id = self._require_external_id(
            condition["external_id"],
            "Condition",
        )
        statement = insert(Condition).values(
            ehr_source_id=ehr_source_id,
            external_id=external_id,
            patient_id=patient_id,
            clinical_status=condition["clinical_status"],
            verification_status=condition["verification_status"],
            code=condition["code"],
            code_system=condition["code_system"],
            display=condition["display"],
            onset_date=condition["onset_date"],
            raw_resource=condition["raw_resource"],
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_conditions_ehr_source_external_id",
            set_={
                "patient_id": statement.excluded.patient_id,
                "clinical_status": statement.excluded.clinical_status,
                "verification_status": statement.excluded.verification_status,
                "code": statement.excluded.code,
                "code_system": statement.excluded.code_system,
                "display": statement.excluded.display,
                "onset_date": statement.excluded.onset_date,
                "raw_resource": statement.excluded.raw_resource,
                "updated_at": func.now(),
            },
        ).returning(Condition)

        result = self.session.execute(
            statement,
            execution_options={"populate_existing": True},
        )
        return result.scalar_one()

    def upsert_medication(
        self,
        ehr_source_id: int,
        patient_id: UUID,
        medication: NormalizedMedicationRequest,
    ) -> Medication:
        """Insert a medication or update it using its source-scoped identity."""

        external_id = self._require_external_id(
            medication["external_id"],
            "MedicationRequest",
        )
        statement = insert(Medication).values(
            ehr_source_id=ehr_source_id,
            external_id=external_id,
            patient_id=patient_id,
            status=medication["status"],
            medication_code=medication["medication_code"],
            medication_display=medication["medication_display"],
            authored_on=medication["authored_on"],
            raw_resource=medication["raw_resource"],
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_medications_ehr_source_external_id",
            set_={
                "patient_id": statement.excluded.patient_id,
                "status": statement.excluded.status,
                "medication_code": statement.excluded.medication_code,
                "medication_display": statement.excluded.medication_display,
                "authored_on": statement.excluded.authored_on,
                "raw_resource": statement.excluded.raw_resource,
                "updated_at": func.now(),
            },
        ).returning(Medication)

        result = self.session.execute(
            statement,
            execution_options={"populate_existing": True},
        )
        return result.scalar_one()

    def list_patients(
        self,
        *,
        source_code: str | None,
        search: str | None,
        limit: int,
        offset: int,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> list[tuple[Patient, str, int, int]]:
        condition_counts = (
            select(
                Condition.patient_id.label("patient_id"),
                func.count(Condition.id).label("condition_count"),
            )
            .group_by(Condition.patient_id)
            .subquery()
        )
        medication_counts = (
            select(
                Medication.patient_id.label("patient_id"),
                func.count(Medication.id).label("medication_count"),
            )
            .group_by(Medication.patient_id)
            .subquery()
        )
        statement = select(
            Patient,
            EHRSource.code,
            func.coalesce(condition_counts.c.condition_count, 0),
            func.coalesce(medication_counts.c.medication_count, 0),
        ).join(
            EHRSource,
            Patient.ehr_source_id == EHRSource.id,
        ).outerjoin(
            condition_counts,
            condition_counts.c.patient_id == Patient.id,
        ).outerjoin(
            medication_counts,
            medication_counts.c.patient_id == Patient.id,
        )

        if source_code:
            statement = statement.where(EHRSource.code == source_code)

        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    Patient.external_id.ilike(pattern),
                    Patient.name.ilike(pattern),
                    Patient.given_name.ilike(pattern),
                    Patient.family_name.ilike(pattern),
                )
            )

        sort_columns = {
            "name": Patient.name,
            "external_id": Patient.external_id,
            "birth_date": Patient.birth_date,
            "gender": Patient.gender,
        }
        sort_column = sort_columns.get(sort_by, Patient.name)
        order_expression = (
            sort_column.desc().nulls_last()
            if sort_order == "desc"
            else sort_column.asc().nulls_last()
        )
        statement = (
            statement.order_by(order_expression, Patient.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return [tuple(row) for row in self.session.execute(statement).all()]

    def get_patient_details(
        self,
        patient_id: UUID,
    ) -> tuple[Patient, str, list[Condition], list[Medication]] | None:
        patient_statement = (
            select(Patient, EHRSource.code)
            .join(EHRSource, Patient.ehr_source_id == EHRSource.id)
            .where(Patient.id == patient_id)
        )
        patient_row = self.session.execute(patient_statement).one_or_none()
        if patient_row is None:
            return None

        conditions = list(
            self.session.execute(
                select(Condition)
                .where(Condition.patient_id == patient_id)
                .order_by(Condition.created_at.asc(), Condition.id.asc())
            )
            .scalars()
            .all()
        )
        medications = list(
            self.session.execute(
                select(Medication)
                .where(Medication.patient_id == patient_id)
                .order_by(Medication.created_at.asc(), Medication.id.asc())
            )
            .scalars()
            .all()
        )
        return patient_row[0], patient_row[1], conditions, medications
