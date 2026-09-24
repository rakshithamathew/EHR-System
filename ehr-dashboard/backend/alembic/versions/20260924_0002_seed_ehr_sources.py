"""Reserve the EHR source seed revision.

Source records are now seeded idempotently at application startup so their
base URLs can come from environment variables.

Revision ID: 20260924_0002
Revises: 20260924_0001
Create Date: 2026-09-24
"""

from collections.abc import Sequence

revision: str = "20260924_0002"
down_revision: str | Sequence[str] | None = "20260924_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
