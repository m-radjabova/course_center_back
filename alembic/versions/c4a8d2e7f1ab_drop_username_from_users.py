"""drop username from users

Revision ID: c4a8d2e7f1ab
Revises: b7e2c4a1f901
Create Date: 2026-04-14 10:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c4a8d2e7f1ab"
down_revision = "b7e2c4a1f901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_users_username_lower", table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")


def downgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    op.execute("UPDATE users SET username = email WHERE username IS NULL")
    op.alter_column("users", "username", nullable=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index("uq_users_username_lower", "users", [sa.literal_column("lower(username)")], unique=True)
