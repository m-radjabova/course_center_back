from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AttendanceStatus, sql_enum

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.lesson import Lesson
    from app.models.user import User


class Attendance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attendance_records"

    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[AttendanceStatus] = mapped_column(
        sql_enum(AttendanceStatus, "attendance_status"),
        nullable=False,
        default=AttendanceStatus.PRESENT,
        server_default=AttendanceStatus.PRESENT.value,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    lesson: Mapped[Lesson] = relationship(back_populates="attendance_records")
    enrollment: Mapped[Enrollment] = relationship(back_populates="attendance_records")
    student: Mapped[User] = relationship(back_populates="attendance_records", foreign_keys=[student_id])

    __table_args__ = (UniqueConstraint("lesson_id", "student_id", name="uq_attendance_lesson_student"),)
