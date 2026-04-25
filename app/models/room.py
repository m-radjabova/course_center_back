from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.course_center import CourseCenter
    from app.models.group import Group


class Room(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rooms"

    course_center_id: Mapped[str] = mapped_column(
        ForeignKey("course_centers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location_note: Mapped[str | None] = mapped_column(String(120), nullable=True)

    course_center: Mapped[CourseCenter] = relationship(back_populates="rooms")
    groups: Mapped[list[Group]] = relationship(back_populates="room")

    __table_args__ = (UniqueConstraint("course_center_id", "name", name="uq_rooms_course_center_name"),)
