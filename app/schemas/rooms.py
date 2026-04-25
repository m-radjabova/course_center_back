from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema


class RoomBase(ORMModel):
    name: str = Field(min_length=1, max_length=20)
    capacity: int = Field(ge=1, le=300)
    location_note: str | None = Field(default=None, max_length=120)


class RoomCreate(RoomBase):
    pass


class RoomUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=20)
    capacity: int | None = Field(default=None, ge=1, le=300)
    location_note: str | None = Field(default=None, max_length=120)


class RoomResponse(TimestampedSchema, RoomBase):
    course_center_id: UUID
