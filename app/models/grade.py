from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.lesson import Lesson
    from app.models.user import User


class Grade(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "grades"

    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    lesson: Mapped[Lesson] = relationship(back_populates="grades")
    enrollment: Mapped[Enrollment] = relationship(back_populates="grades")
    student: Mapped[User] = relationship(back_populates="grades_received", foreign_keys=[student_id])
    teacher: Mapped[User | None] = relationship(back_populates="grades_given", foreign_keys=[teacher_id])

    __table_args__ = (
        UniqueConstraint("lesson_id", "student_id", name="uq_grades_lesson_student"),
        CheckConstraint("score >= 0 AND score <= 100", name="ck_grades_score_percentage"),
    )
