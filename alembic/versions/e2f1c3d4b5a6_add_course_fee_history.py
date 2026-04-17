"""add_course_fee_history

Revision ID: e2f1c3d4b5a6
Revises: d1a2b3c4e5f6
Create Date: 2026-04-15 21:30:00.000000

"""
from datetime import date
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f1c3d4b5a6"
down_revision: Union[str, None] = "d1a2b3c4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_fee_histories",
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "effective_from", name="uq_course_fee_history_course_effective_from"),
    )
    op.create_index(op.f("ix_course_fee_histories_course_id"), "course_fee_histories", ["course_id"], unique=False)

    connection = op.get_bind()
    course_rows = connection.execute(
        sa.text("SELECT id, default_monthly_fee, created_at FROM courses")
    ).mappings().all()

    for row in course_rows:
        created_at = row["created_at"]
        created_date = created_at.date() if created_at else date.today()
        effective_from = date(created_date.year, created_date.month, 1)
        connection.execute(
            sa.text(
                """
                INSERT INTO course_fee_histories (id, course_id, amount, effective_from, created_at, updated_at)
                VALUES (:id, :course_id, :amount, :effective_from, now(), now())
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "course_id": str(row["id"]),
                "amount": row["default_monthly_fee"],
                "effective_from": effective_from,
            },
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_course_fee_histories_course_id"), table_name="course_fee_histories")
    op.drop_table("course_fee_histories")
