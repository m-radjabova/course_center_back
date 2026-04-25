from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.group import Group
    from app.models.room import Room
    from app.models.user import User


class CourseCenter(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "course_centers"

    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    users: Mapped[list[User]] = relationship(back_populates="course_center")
    courses: Mapped[list[Course]] = relationship(back_populates="course_center")
    rooms: Mapped[list[Room]] = relationship(back_populates="course_center")
    groups: Mapped[list[Group]] = relationship(back_populates="course_center")
