"""add_multi_tenant_course_centers

Revision ID: 4b7c3d2e1f0a
Revises: e2f1c3d4b5a6
Create Date: 2026-04-25 19:45:00.000000
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "4b7c3d2e1f0a"
down_revision: Union[str, Sequence[str], None] = "e2f1c3d4b5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'super_admin'")

    op.create_table(
        "course_centers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_course_centers_name"), "course_centers", ["name"], unique=False)
    op.create_index(op.f("ix_course_centers_slug"), "course_centers", ["slug"], unique=False)

    default_center_id = uuid.uuid4()
    course_centers_table = sa.table(
        "course_centers",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        course_centers_table,
        [
            {
                "id": default_center_id,
                "name": "Default Course Center",
                "slug": "default",
                "description": "Migrated default tenant for existing data",
                "is_active": True,
            }
        ],
    )

    for table_name in ("users", "courses", "rooms", "groups"):
        op.add_column(table_name, sa.Column("course_center_id", postgresql.UUID(as_uuid=True), nullable=True))

    op.execute(
        sa.text("UPDATE users SET course_center_id = :course_center_id").bindparams(course_center_id=default_center_id)
    )
    op.execute(
        sa.text("UPDATE courses SET course_center_id = :course_center_id").bindparams(course_center_id=default_center_id)
    )
    op.execute(
        sa.text("UPDATE rooms SET course_center_id = :course_center_id").bindparams(course_center_id=default_center_id)
    )
    op.execute(
        """
        UPDATE groups AS g
        SET course_center_id = c.course_center_id
        FROM courses AS c
        WHERE g.course_id = c.id
        """
    )
    op.execute(
        sa.text(
            "UPDATE groups SET course_center_id = :course_center_id WHERE course_center_id IS NULL"
        ).bindparams(course_center_id=default_center_id)
    )

    op.alter_column("users", "course_center_id", nullable=False)
    op.alter_column("courses", "course_center_id", nullable=False)
    op.alter_column("rooms", "course_center_id", nullable=False)
    op.alter_column("groups", "course_center_id", nullable=False)

    op.create_index(op.f("ix_users_course_center_id"), "users", ["course_center_id"], unique=False)
    op.create_index(op.f("ix_courses_course_center_id"), "courses", ["course_center_id"], unique=False)
    op.create_index(op.f("ix_rooms_course_center_id"), "rooms", ["course_center_id"], unique=False)
    op.create_index(op.f("ix_groups_course_center_id"), "groups", ["course_center_id"], unique=False)

    op.create_foreign_key(
        "fk_users_course_center_id",
        "users",
        "course_centers",
        ["course_center_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_courses_course_center_id",
        "courses",
        "course_centers",
        ["course_center_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_rooms_course_center_id",
        "rooms",
        "course_centers",
        ["course_center_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_groups_course_center_id",
        "groups",
        "course_centers",
        ["course_center_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute("ALTER TABLE courses DROP CONSTRAINT IF EXISTS courses_name_key")
    op.execute("ALTER TABLE rooms DROP CONSTRAINT IF EXISTS rooms_name_key")
    op.create_unique_constraint("uq_courses_course_center_name", "courses", ["course_center_id", "name"])
    op.create_unique_constraint("uq_rooms_course_center_name", "rooms", ["course_center_id", "name"])


def downgrade() -> None:
    op.drop_constraint("uq_rooms_course_center_name", "rooms", type_="unique")
    op.drop_constraint("uq_courses_course_center_name", "courses", type_="unique")
    op.create_unique_constraint("courses_name_key", "courses", ["name"])
    op.create_unique_constraint("rooms_name_key", "rooms", ["name"])

    op.drop_constraint("fk_groups_course_center_id", "groups", type_="foreignkey")
    op.drop_constraint("fk_rooms_course_center_id", "rooms", type_="foreignkey")
    op.drop_constraint("fk_courses_course_center_id", "courses", type_="foreignkey")
    op.drop_constraint("fk_users_course_center_id", "users", type_="foreignkey")

    op.drop_index(op.f("ix_groups_course_center_id"), table_name="groups")
    op.drop_index(op.f("ix_rooms_course_center_id"), table_name="rooms")
    op.drop_index(op.f("ix_courses_course_center_id"), table_name="courses")
    op.drop_index(op.f("ix_users_course_center_id"), table_name="users")

    op.drop_column("groups", "course_center_id")
    op.drop_column("rooms", "course_center_id")
    op.drop_column("courses", "course_center_id")
    op.drop_column("users", "course_center_id")

    op.drop_index(op.f("ix_course_centers_slug"), table_name="course_centers")
    op.drop_index(op.f("ix_course_centers_name"), table_name="course_centers")
    op.drop_table("course_centers")
