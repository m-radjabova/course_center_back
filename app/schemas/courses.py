from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema


class CourseFeeHistoryResponse(TimestampedSchema):
    amount: Decimal
    effective_from: date


class CourseBase(ORMModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    default_monthly_fee: Decimal = Field(ge=0)
    is_active: bool = True


class CourseCreate(CourseBase):
    fee_effective_from: date | None = None


class CourseUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    default_monthly_fee: Decimal | None = Field(default=None, ge=0)
    fee_effective_from: date | None = None
    is_active: bool | None = None


class CourseResponse(TimestampedSchema, CourseBase):
    course_center_id: UUID
    fee_histories: list[CourseFeeHistoryResponse] = Field(default_factory=list)
