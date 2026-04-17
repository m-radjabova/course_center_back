from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PaymentMethod, PaymentStatus, sql_enum

if TYPE_CHECKING:
    from app.models.enrollment import Enrollment
    from app.models.group import Group
    from app.models.user import User


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    student_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id: Mapped[str] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id: Mapped[str | None] = mapped_column(ForeignKey("enrollments.id", ondelete="SET NULL"), nullable=True, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    month_for: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    method: Mapped[PaymentMethod] = mapped_column(sql_enum(PaymentMethod, "payment_method"), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(sql_enum(PaymentStatus, "payment_status"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    student: Mapped[User] = relationship(back_populates="payments", foreign_keys=[student_id])
    group: Mapped[Group] = relationship(back_populates="payments")
    enrollment: Mapped[Enrollment | None] = relationship(back_populates="payments")
