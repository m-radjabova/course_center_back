"""add telegram fields to student profiles

Revision ID: a7f3d9c2b1e4
Revises: f4c7a9b2d1e0
Create Date: 2026-04-16 19:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a7f3d9c2b1e4"
down_revision = "f4c7a9b2d1e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("student_profiles", sa.Column("telegram_chat_id", sa.String(length=64), nullable=True))
    op.add_column("student_profiles", sa.Column("telegram_username", sa.String(length=255), nullable=True))
    op.add_column("student_profiles", sa.Column("telegram_first_name", sa.String(length=255), nullable=True))
    op.add_column("student_profiles", sa.Column("telegram_connected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("student_profiles", sa.Column("telegram_link_token", sa.String(length=255), nullable=True))
    op.add_column("student_profiles", sa.Column("telegram_link_token_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("student_profiles", sa.Column("telegram_last_credentials_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_student_profiles_telegram_chat_id"), "student_profiles", ["telegram_chat_id"], unique=False)
    op.create_index(op.f("ix_student_profiles_telegram_link_token"), "student_profiles", ["telegram_link_token"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_student_profiles_telegram_link_token"), table_name="student_profiles")
    op.drop_index(op.f("ix_student_profiles_telegram_chat_id"), table_name="student_profiles")
    op.drop_column("student_profiles", "telegram_last_credentials_sent_at")
    op.drop_column("student_profiles", "telegram_link_token_expires_at")
    op.drop_column("student_profiles", "telegram_link_token")
    op.drop_column("student_profiles", "telegram_connected_at")
    op.drop_column("student_profiles", "telegram_first_name")
    op.drop_column("student_profiles", "telegram_username")
    op.drop_column("student_profiles", "telegram_chat_id")
