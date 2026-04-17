from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class TeacherProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "teacher_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    specialization: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    hired_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    user: Mapped[User] = relationship(back_populates="teacher_profile")


class StudentProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_by_teacher_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parent_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_link_token: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    telegram_link_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    telegram_last_credentials_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="student_profile", foreign_keys=[user_id])
    created_by_teacher: Mapped[User | None] = relationship(
        back_populates="created_students",
        foreign_keys=[created_by_teacher_id],
    )
