"""initial_course_center_schema

Revision ID: 9f4a2c1b7d01
Revises:
Create Date: 2026-04-13 21:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f4a2c1b7d01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_monthly_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_name"), "courses", ["name"], unique=True)

    op.create_table(
        "rooms",
        sa.Column("name", sa.String(length=20), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("location_note", sa.String(length=120), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rooms_name"), "rooms", ["name"], unique=True)

    op.create_table(
        "users",
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("admin", "teacher", "student", name="user_role"), nullable=False),
        sa.Column("status", sa.Enum("active", "inactive", name="user_status"), server_default="active", nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)
    op.create_index("uq_users_username_lower", "users", [sa.literal_column("lower(username)")], unique=True)

    op.create_table(
        "student_profiles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("created_by_teacher_id", sa.UUID(), nullable=True),
        sa.Column("parent_name", sa.String(length=120), nullable=True),
        sa.Column("parent_phone", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra_info", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_teacher_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "teacher_profiles",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("specialization", sa.String(length=120), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("hired_at", sa.Date(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "groups",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("course_id", sa.UUID(), nullable=False),
        sa.Column("teacher_id", sa.UUID(), nullable=True),
        sa.Column("room_id", sa.UUID(), nullable=True),
        sa.Column("monthly_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum("planned", "active", "finished", "archived", name="group_status"), server_default="planned", nullable=False),
        sa.Column("schedule_summary", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("course_id", "name", name="uq_groups_course_name"),
    )
    op.create_index(op.f("ix_groups_course_id"), "groups", ["course_id"], unique=False)
    op.create_index(op.f("ix_groups_teacher_id"), "groups", ["teacher_id"], unique=False)
    op.create_index(op.f("ix_groups_room_id"), "groups", ["room_id"], unique=False)

    op.create_table(
        "enrollments",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("enrolled_at", sa.Date(), nullable=False),
        sa.Column("left_at", sa.Date(), nullable=True),
        sa.Column("status", sa.Enum("active", "left", "finished", name="enrollment_status"), server_default="active", nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "group_id", name="uq_enrollments_student_group"),
    )
    op.create_index(op.f("ix_enrollments_group_id"), "enrollments", ["group_id"], unique=False)
    op.create_index(op.f("ix_enrollments_student_id"), "enrollments", ["student_id"], unique=False)

    op.create_table(
        "lessons",
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("lesson_number", sa.Integer(), nullable=False),
        sa.Column("lesson_date", sa.Date(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=True),
        sa.Column("homework", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "lesson_number", name="uq_lessons_group_number"),
    )
    op.create_index(op.f("ix_lessons_group_id"), "lessons", ["group_id"], unique=False)
    op.create_index(op.f("ix_lessons_lesson_date"), "lessons", ["lesson_date"], unique=False)

    op.create_table(
        "attendance_records",
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("enrollment_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Enum("present", "absent", "late", name="attendance_status"), server_default="present", nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", "student_id", name="uq_attendance_lesson_student"),
    )
    op.create_index(op.f("ix_attendance_records_lesson_id"), "attendance_records", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_attendance_records_enrollment_id"), "attendance_records", ["enrollment_id"], unique=False)
    op.create_index(op.f("ix_attendance_records_student_id"), "attendance_records", ["student_id"], unique=False)

    op.create_table(
        "grades",
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("enrollment_id", sa.UUID(), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("teacher_id", sa.UUID(), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_grades_score_percentage"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lesson_id", "student_id", name="uq_grades_lesson_student"),
    )
    op.create_index(op.f("ix_grades_lesson_id"), "grades", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_grades_enrollment_id"), "grades", ["enrollment_id"], unique=False)
    op.create_index(op.f("ix_grades_student_id"), "grades", ["student_id"], unique=False)
    op.create_index(op.f("ix_grades_teacher_id"), "grades", ["teacher_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("group_id", sa.UUID(), nullable=False),
        sa.Column("enrollment_id", sa.UUID(), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("month_for", sa.Date(), nullable=False),
        sa.Column("method", sa.Enum("cash", "card", name="payment_method"), nullable=False),
        sa.Column("status", sa.Enum("pending", "paid", "failed", "refunded", name="payment_status"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_student_id"), "payments", ["student_id"], unique=False)
    op.create_index(op.f("ix_payments_group_id"), "payments", ["group_id"], unique=False)
    op.create_index(op.f("ix_payments_enrollment_id"), "payments", ["enrollment_id"], unique=False)
    op.create_index(op.f("ix_payments_month_for"), "payments", ["month_for"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_month_for"), table_name="payments")
    op.drop_index(op.f("ix_payments_enrollment_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_group_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_student_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_grades_teacher_id"), table_name="grades")
    op.drop_index(op.f("ix_grades_student_id"), table_name="grades")
    op.drop_index(op.f("ix_grades_enrollment_id"), table_name="grades")
    op.drop_index(op.f("ix_grades_lesson_id"), table_name="grades")
    op.drop_table("grades")
    op.drop_index(op.f("ix_attendance_records_student_id"), table_name="attendance_records")
    op.drop_index(op.f("ix_attendance_records_enrollment_id"), table_name="attendance_records")
    op.drop_index(op.f("ix_attendance_records_lesson_id"), table_name="attendance_records")
    op.drop_table("attendance_records")
    op.drop_index(op.f("ix_lessons_lesson_date"), table_name="lessons")
    op.drop_index(op.f("ix_lessons_group_id"), table_name="lessons")
    op.drop_table("lessons")
    op.drop_index(op.f("ix_enrollments_student_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_group_id"), table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_index(op.f("ix_groups_room_id"), table_name="groups")
    op.drop_index(op.f("ix_groups_teacher_id"), table_name="groups")
    op.drop_index(op.f("ix_groups_course_id"), table_name="groups")
    op.drop_table("groups")
    op.drop_table("teacher_profiles")
    op.drop_table("student_profiles")
    op.drop_index("uq_users_username_lower", table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_rooms_name"), table_name="rooms")
    op.drop_table("rooms")
    op.drop_index(op.f("ix_courses_name"), table_name="courses")
    op.drop_table("courses")
