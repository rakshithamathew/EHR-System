"""Add patient sync metadata and cascading clinical-resource deletes.

Revision ID: 20260925_0003
Revises: 20260924_0002
Create Date: 2026-09-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260925_0003"
down_revision: str | Sequence[str] | None = "20260924_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "patients",
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.drop_constraint(
        "fk_conditions_patient_id_patients",
        "conditions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_conditions_patient_id_patients",
        "conditions",
        "patients",
        ["patient_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "fk_medications_patient_id_patients",
        "medications",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_medications_patient_id_patients",
        "medications",
        "patients",
        ["patient_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_medications_patient_id_patients",
        "medications",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_medications_patient_id_patients",
        "medications",
        "patients",
        ["patient_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_conditions_patient_id_patients",
        "conditions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_conditions_patient_id_patients",
        "conditions",
        "patients",
        ["patient_id"],
        ["id"],
    )
    op.drop_column("patients", "last_synced_at")
