from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import GroupStatus, sql_enum

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.enrollment import Enrollment
    from app.models.lesson import Lesson
    from app.models.payment import Payment
    from app.models.room import Room
    from app.models.user import User


class Group(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    course_id: Mapped[str] = mapped_column(ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False, index=True)
    teacher_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    room_id: Mapped[str | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[GroupStatus] = mapped_column(
        sql_enum(GroupStatus, "group_status"),
        nullable=False,
        default=GroupStatus.PLANNED,
        server_default=GroupStatus.PLANNED.value,
    )
    schedule_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    course: Mapped[Course] = relationship(back_populates="groups")
    teacher: Mapped[User | None] = relationship(back_populates="teaching_groups", foreign_keys=[teacher_id])
    room: Mapped[Room | None] = relationship(back_populates="groups")
    enrollments: Mapped[list[Enrollment]] = relationship(back_populates="group", cascade="all, delete-orphan")
    lessons: Mapped[list[Lesson]] = relationship(back_populates="group", cascade="all, delete-orphan")
    payments: Mapped[list[Payment]] = relationship(back_populates="group")

    __table_args__ = (UniqueConstraint("course_id", "name", name="uq_groups_course_name"),)
