"""drop_is_superuser

Revision ID: 8c2d4e1f9ab3
Revises: 31b9d0d5f6c2
Create Date: 2026-04-13 22:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "8c2d4e1f9ab3"
down_revision: Union[str, None] = "31b9d0d5f6c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_superuser" in columns:
        op.drop_column("users", "is_superuser")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_superuser" not in columns:
        op.add_column(
            "users",
            sa.Column("is_superuser", sa.Boolean(), server_default="false", nullable=False),
        )
