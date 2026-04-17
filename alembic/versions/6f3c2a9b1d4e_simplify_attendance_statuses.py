"""simplify_attendance_statuses

Revision ID: 6f3c2a9b1d4e
Revises: 8c2d4e1f9ab3
Create Date: 2026-04-14 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "6f3c2a9b1d4e"
down_revision: Union[str, None] = "8c2d4e1f9ab3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE attendance_records SET status = 'present' WHERE status = 'late'")
    op.execute("ALTER TYPE attendance_status RENAME TO attendance_status_old")
    op.execute("CREATE TYPE attendance_status AS ENUM ('present', 'absent')")
    op.execute(
        """
        ALTER TABLE attendance_records
        ALTER COLUMN status DROP DEFAULT,
        ALTER COLUMN status TYPE attendance_status
        USING status::text::attendance_status,
        ALTER COLUMN status SET DEFAULT 'present'
        """
    )
    op.execute("DROP TYPE attendance_status_old")


def downgrade() -> None:
    op.execute("ALTER TYPE attendance_status RENAME TO attendance_status_old")
    op.execute("CREATE TYPE attendance_status AS ENUM ('present', 'absent', 'late')")
    op.execute(
        """
        ALTER TABLE attendance_records
        ALTER COLUMN status DROP DEFAULT,
        ALTER COLUMN status TYPE attendance_status
        USING status::text::attendance_status,
        ALTER COLUMN status SET DEFAULT 'present'
        """
    )
    op.execute("DROP TYPE attendance_status_old")
