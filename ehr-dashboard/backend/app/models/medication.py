from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = (
        UniqueConstraint(
            "ehr_source_id",
            "external_id",
            name="uq_medications_ehr_source_external_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    ehr_source_id: Mapped[int] = mapped_column(
        ForeignKey("ehr_sources.id"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("patients.id"),
        nullable=False,
    )
    status: Mapped[str | None] = mapped_column(String(100))
    medication_code: Mapped[str | None] = mapped_column(String(255))
    medication_display: Mapped[str | None] = mapped_column(Text)
    authored_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_resource: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
