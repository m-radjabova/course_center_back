from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.groups import GroupResponse


class LessonBase(ORMModel):
    group_id: UUID
    lesson_number: int | None = Field(default=None, ge=1, le=500)
    lesson_date: date
    topic: str | None = Field(default=None, max_length=255)
    homework: str | None = None
    notes: str | None = None


class LessonCreate(LessonBase):
    pass


class LessonUpdate(ORMModel):
    lesson_number: int | None = Field(default=None, ge=1, le=500)
    lesson_date: date | None = None
    topic: str | None = Field(default=None, max_length=255)
    homework: str | None = None
    notes: str | None = None


class LessonResponse(TimestampedSchema, LessonBase):
    group: GroupResponse
