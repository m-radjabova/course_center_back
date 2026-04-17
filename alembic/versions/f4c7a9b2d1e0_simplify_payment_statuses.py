"""simplify_payment_statuses

Revision ID: f4c7a9b2d1e0
Revises: e2f1c3d4b5a6
Create Date: 2026-04-15 22:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4c7a9b2d1e0"
down_revision: Union[str, None] = "e2f1c3d4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    op.execute("UPDATE payments SET status = 'pending' WHERE status IN ('failed', 'refunded')")
    if _table_exists("monthly_payments"):
        op.execute("UPDATE monthly_payments SET status = 'pending' WHERE status IN ('failed', 'refunded')")
    op.execute("ALTER TYPE payment_status RENAME TO payment_status_old")
    op.execute("CREATE TYPE payment_status AS ENUM ('pending', 'paid')")
    op.execute(
        """
        ALTER TABLE payments
        ALTER COLUMN status DROP DEFAULT,
        ALTER COLUMN status TYPE payment_status
        USING status::text::payment_status
        """
    )
    if _table_exists("monthly_payments"):
        op.execute(
            """
            ALTER TABLE monthly_payments
            ALTER COLUMN status DROP DEFAULT,
            ALTER COLUMN status TYPE payment_status
            USING status::text::payment_status,
            ALTER COLUMN status SET DEFAULT 'pending'
            """
        )
    op.execute("DROP TYPE payment_status_old")


def downgrade() -> None:
    op.execute("ALTER TYPE payment_status RENAME TO payment_status_old")
    op.execute("CREATE TYPE payment_status AS ENUM ('pending', 'paid', 'failed', 'refunded')")
    op.execute(
        """
        ALTER TABLE payments
        ALTER COLUMN status DROP DEFAULT,
        ALTER COLUMN status TYPE payment_status
        USING status::text::payment_status
        """
    )
    if _table_exists("monthly_payments"):
        op.execute(
            """
            ALTER TABLE monthly_payments
            ALTER COLUMN status DROP DEFAULT,
            ALTER COLUMN status TYPE payment_status
            USING status::text::payment_status,
            ALTER COLUMN status SET DEFAULT 'pending'
            """
        )
    op.execute("DROP TYPE payment_status_old")
