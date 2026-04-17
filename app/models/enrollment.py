from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import EnrollmentStatus, sql_enum

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.grade import Grade
    from app.models.group import Group
    from app.models.payment import Payment
    from app.models.user import User


class Enrollment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "enrollments"

    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_at: Mapped[date] = mapped_column(Date, nullable=False)
    left_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[EnrollmentStatus] = mapped_column(
        sql_enum(EnrollmentStatus, "enrollment_status"),
        nullable=False,
        default=EnrollmentStatus.ACTIVE,
        server_default=EnrollmentStatus.ACTIVE.value,
    )

    student: Mapped[User] = relationship(back_populates="enrollments", foreign_keys=[student_id])
    group: Mapped[Group] = relationship(back_populates="enrollments")
    attendance_records: Mapped[list[Attendance]] = relationship(back_populates="enrollment", cascade="all, delete-orphan")
    grades: Mapped[list[Grade]] = relationship(back_populates="enrollment")
    payments: Mapped[list[Payment]] = relationship(back_populates="enrollment")

    __table_args__ = (UniqueConstraint("student_id", "group_id", name="uq_enrollments_student_group"),)
