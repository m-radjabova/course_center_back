"""drop salary_amount from teacher_profiles

Revision ID: d1a2b3c4e5f6
Revises: c4a8d2e7f1ab
Create Date: 2026-04-14 20:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "d1a2b3c4e5f6"
down_revision: Union[str, None] = "c4a8d2e7f1ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("teacher_profiles")}
    if "salary_amount" in columns:
        op.drop_column("teacher_profiles", "salary_amount")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("teacher_profiles")}
    if "salary_amount" not in columns:
        op.add_column("teacher_profiles", sa.Column("salary_amount", sa.Numeric(12, 2), nullable=True))
