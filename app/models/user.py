from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole, UserStatus, sql_enum
from app.models.enums import EnrollmentStatus

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.course_center import CourseCenter
    from app.models.enrollment import Enrollment
    from app.models.grade import Grade
    from app.models.group import Group
    from app.models.payment import Payment
    from app.models.profile import StudentProfile, TeacherProfile


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    course_center_id: Mapped[str] = mapped_column(
        ForeignKey("course_centers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    roles: Mapped[list[UserRole]] = mapped_column(
        ARRAY(sql_enum(UserRole, "user_role")),
        nullable=False,
        default=lambda: [UserRole.STUDENT],
        server_default=text("ARRAY['student']::user_role[]"),
    )
    status: Mapped[UserStatus] = mapped_column(
        sql_enum(UserStatus, "user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    course_center: Mapped[CourseCenter] = relationship(back_populates="users")

    teacher_profile: Mapped[TeacherProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        foreign_keys="TeacherProfile.user_id",
    )
    student_profile: Mapped[StudentProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        foreign_keys="StudentProfile.user_id",
    )
    teaching_groups: Mapped[list[Group]] = relationship(
        back_populates="teacher",
        foreign_keys="Group.teacher_id",
    )
    created_students: Mapped[list[StudentProfile]] = relationship(
        back_populates="created_by_teacher",
        foreign_keys="StudentProfile.created_by_teacher_id",
    )
    enrollments: Mapped[list[Enrollment]] = relationship(
        back_populates="student",
        foreign_keys="Enrollment.student_id",
        cascade="all, delete-orphan",
    )
    attendance_records: Mapped[list[Attendance]] = relationship(
        back_populates="student",
        foreign_keys="Attendance.student_id",
    )
    grades_given: Mapped[list[Grade]] = relationship(
        back_populates="teacher",
        foreign_keys="Grade.teacher_id",
    )
    grades_received: Mapped[list[Grade]] = relationship(
        back_populates="student",
        foreign_keys="Grade.student_id",
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="student",
        foreign_keys="Payment.student_id",
    )

    def has_role(self, role: UserRole) -> bool:
        return role in self.roles

    def has_any_role(self, *roles: UserRole) -> bool:
        return any(role in self.roles for role in roles)

    @property
    def course_center_name(self) -> str | None:
        return self.course_center.name if self.course_center else None

    @property
    def active_group_ids(self) -> list[str]:
        return [
            str(enrollment.group_id)
            for enrollment in self.enrollments
            if enrollment.status == EnrollmentStatus.ACTIVE
        ]

    @property
    def active_group_names(self) -> list[str]:
        return [
            enrollment.group.name
            for enrollment in self.enrollments
            if enrollment.status == EnrollmentStatus.ACTIVE and enrollment.group
        ]

    __table_args__ = (
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )
