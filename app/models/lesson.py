from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.attendance import Attendance
    from app.models.grade import Grade
    from app.models.group import Group


class Lesson(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "lessons"

    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lesson_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    homework: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    group: Mapped[Group] = relationship(back_populates="lessons")
    attendance_records: Mapped[list[Attendance]] = relationship(back_populates="lesson", cascade="all, delete-orphan")
    grades: Mapped[list[Grade]] = relationship(back_populates="lesson", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("group_id", "lesson_number", name="uq_lessons_group_number"),)
