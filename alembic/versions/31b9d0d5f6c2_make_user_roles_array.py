"""make_user_roles_array

Revision ID: 31b9d0d5f6c2
Revises: 9f4a2c1b7d01
Create Date: 2026-04-13 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "31b9d0d5f6c2"
down_revision: Union[str, None] = "9f4a2c1b7d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "roles",
            postgresql.ARRAY(sa.Enum("admin", "teacher", "student", name="user_role", create_type=False)),
            nullable=False,
            server_default=sa.text("ARRAY['student']::user_role[]"),
        ),
    )
    op.execute("UPDATE users SET roles = ARRAY[role]::user_role[]")
    op.drop_column("users", "role")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.Enum("admin", "teacher", "student", name="user_role", create_type=False),
            nullable=False,
            server_default="student",
        ),
    )
    op.add_column("users", sa.Column("is_superuser", sa.Boolean(), server_default="false", nullable=False))
    op.execute("UPDATE users SET role = COALESCE(roles[1], 'student'::user_role)")
    op.drop_column("users", "roles")
