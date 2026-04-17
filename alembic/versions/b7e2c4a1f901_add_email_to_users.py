"""add_email_to_users

Revision ID: b7e2c4a1f901
Revises: 6f3c2a9b1d4e
Create Date: 2026-04-14 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e2c4a1f901"
down_revision: Union[str, None] = "6f3c2a9b1d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))
    op.execute(
        """
        UPDATE users
        SET email = CASE
            WHEN position('@' in username) > 1 THEN lower(username)
            ELSE lower(username || '@course-center.local')
        END
        """
    )
    op.alter_column("users", "email", nullable=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index("uq_users_email_lower", "users", [sa.literal_column("lower(email)")], unique=True)


def downgrade() -> None:
    op.drop_index("uq_users_email_lower", table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_column("users", "email")
