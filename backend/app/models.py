from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EHRSource(Base):
    __tablename__ = "ehr_sources"
    __table_args__ = (UniqueConstraint("code", name="uq_ehr_sources_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (UniqueConstraint("ehr_source_id", "external_id", name="uq_patients_ehr_source_external_id"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ehr_source_id: Mapped[int] = mapped_column(ForeignKey("ehr_sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(512))
    given_name: Mapped[str | None] = mapped_column(String(255))
    family_name: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(50))
    birth_date: Mapped[date | None] = mapped_column(Date)
    raw_resource: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Condition(Base):
    __tablename__ = "conditions"
    __table_args__ = (UniqueConstraint("ehr_source_id", "external_id", name="uq_conditions_ehr_source_external_id"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ehr_source_id: Mapped[int] = mapped_column(ForeignKey("ehr_sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    clinical_status: Mapped[str | None] = mapped_column(String(100))
    verification_status: Mapped[str | None] = mapped_column(String(100))
    code: Mapped[str | None] = mapped_column(String(255))
    code_system: Mapped[str | None] = mapped_column(String(512))
    display: Mapped[str | None] = mapped_column(Text)
    onset_date: Mapped[date | None] = mapped_column(Date)
    raw_resource: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = (UniqueConstraint("ehr_source_id", "external_id", name="uq_medications_ehr_source_external_id"),)
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ehr_source_id: Mapped[int] = mapped_column(ForeignKey("ehr_sources.id"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str | None] = mapped_column(String(100))
    medication_code: Mapped[str | None] = mapped_column(String(255))
    medication_display: Mapped[str | None] = mapped_column(Text)
    authored_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_resource: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SyncRun(Base):
    __tablename__ = "sync_runs"
    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    ehr_source_id: Mapped[int] = mapped_column(ForeignKey("ehr_sources.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patients_processed: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    conditions_processed: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    medications_processed: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    error_message: Mapped[str | None] = mapped_column(Text)
