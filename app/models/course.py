from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.course_center import CourseCenter
    from app.models.group import Group


class CourseFeeHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "course_fee_histories"

    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)

    course: Mapped["Course"] = relationship(back_populates="fee_histories")

    __table_args__ = (UniqueConstraint("course_id", "effective_from", name="uq_course_fee_history_course_effective_from"),)


class Course(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "courses"

    course_center_id: Mapped[str] = mapped_column(
        ForeignKey("course_centers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_monthly_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    course_center: Mapped[CourseCenter] = relationship(back_populates="courses")
    groups: Mapped[list[Group]] = relationship(back_populates="course")
    fee_histories: Mapped[list[CourseFeeHistory]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by=lambda: (CourseFeeHistory.effective_from.desc(), CourseFeeHistory.created_at.desc()),
    )

    __table_args__ = (UniqueConstraint("course_center_id", "name", name="uq_courses_course_center_name"),)
