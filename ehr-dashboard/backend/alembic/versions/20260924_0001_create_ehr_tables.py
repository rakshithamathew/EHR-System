"""Create the core EHR tables.

Revision ID: 20260924_0001
Revises:
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260924_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ehr_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_ehr_sources_code"),
    )

    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ehr_source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("given_name", sa.String(length=255), nullable=True),
        sa.Column("family_name", sa.String(length=255), nullable=True),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("raw_resource", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ehr_source_id"],
            ["ehr_sources.id"],
            name="fk_patients_ehr_source_id_ehr_sources",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ehr_source_id",
            "external_id",
            name="uq_patients_ehr_source_external_id",
        ),
    )

    op.create_table(
        "conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ehr_source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_status", sa.String(length=100), nullable=True),
        sa.Column("verification_status", sa.String(length=100), nullable=True),
        sa.Column("code", sa.String(length=255), nullable=True),
        sa.Column("code_system", sa.String(length=512), nullable=True),
        sa.Column("display", sa.Text(), nullable=True),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("raw_resource", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ehr_source_id"],
            ["ehr_sources.id"],
            name="fk_conditions_ehr_source_id_ehr_sources",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_conditions_patient_id_patients",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ehr_source_id",
            "external_id",
            name="uq_conditions_ehr_source_external_id",
        ),
    )

    op.create_table(
        "medications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ehr_source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=100), nullable=True),
        sa.Column("medication_code", sa.String(length=255), nullable=True),
        sa.Column("medication_display", sa.Text(), nullable=True),
        sa.Column("authored_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_resource", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ehr_source_id"],
            ["ehr_sources.id"],
            name="fk_medications_ehr_source_id_ehr_sources",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_medications_patient_id_patients",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ehr_source_id",
            "external_id",
            name="uq_medications_ehr_source_external_id",
        ),
    )

    op.create_table(
        "sync_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ehr_source_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "patients_processed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "conditions_processed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "medications_processed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ehr_source_id"],
            ["ehr_sources.id"],
            name="fk_sync_runs_ehr_source_id_ehr_sources",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("sync_runs")
    op.drop_table("medications")
    op.drop_table("conditions")
    op.drop_table("patients")
    op.drop_table("ehr_sources")
