from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.courses import CourseResponse
from app.schemas.enums import GroupStatus
from app.schemas.rooms import RoomResponse
from app.schemas.users import UserResponse


class GroupBase(ORMModel):
    name: str = Field(min_length=2, max_length=120)
    course_id: UUID
    teacher_id: UUID | None = None
    room_id: UUID | None = None
    monthly_fee: Decimal = Field(ge=0)
    start_date: date
    end_date: date | None = None
    status: GroupStatus = GroupStatus.PLANNED
    schedule_summary: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class GroupCreate(GroupBase):
    course_center_id: UUID | None = None


class GroupUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    course_id: UUID | None = None
    teacher_id: UUID | None = None
    room_id: UUID | None = None
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    status: GroupStatus | None = None
    schedule_summary: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class GroupResponse(TimestampedSchema):
    name: str
    course_center_id: UUID
    course_id: UUID
    teacher_id: UUID | None = None
    room_id: UUID | None = None
    monthly_fee: Decimal
    start_date: date
    end_date: date | None = None
    status: GroupStatus
    schedule_summary: str | None = None
    notes: str | None = None
    course: CourseResponse
    teacher: UserResponse | None = None
    room: RoomResponse | None = None
