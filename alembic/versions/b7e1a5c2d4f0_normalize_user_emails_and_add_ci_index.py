"""normalize user emails and add case-insensitive unique index

Revision ID: b7e1a5c2d4f0
Revises: 9d71c2c4c001
Create Date: 2026-04-06 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e1a5c2d4f0"
down_revision: Union[str, None] = "9d71c2c4c001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {idx.get("name") for idx in inspector.get_indexes("users")}

    op.execute("UPDATE users SET email = lower(trim(email)) WHERE email IS NOT NULL")

    duplicate_emails = bind.execute(
        sa.text(
            """
            SELECT lower(email) AS normalized_email
            FROM users
            GROUP BY lower(email)
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()

    if duplicate_emails:
        duplicates = ", ".join(row.normalized_email for row in duplicate_emails)
        raise RuntimeError(
            f"Cannot create case-insensitive unique index because duplicate emails exist: {duplicates}"
        )

    if "uq_users_email_lower" not in existing_indexes:
        op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {idx.get("name") for idx in inspector.get_indexes("users")}

    if "uq_users_email_lower" in existing_indexes:
        op.drop_index("uq_users_email_lower", table_name="users")
