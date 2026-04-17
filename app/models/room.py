from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.group import Group


class Room(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rooms"

    name: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location_note: Mapped[str | None] = mapped_column(String(120), nullable=True)

    groups: Mapped[list[Group]] = relationship(back_populates="room")
