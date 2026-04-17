from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.enums import EnrollmentStatus
from app.schemas.profiles import StudentDetailResponse
from app.schemas.groups import GroupResponse


class EnrollmentBase(ORMModel):
    student_id: UUID
    group_id: UUID
    enrolled_at: date
    left_at: date | None = None
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class EnrollmentCreate(EnrollmentBase):
    pass


class BulkEnrollmentCreate(ORMModel):
    student_ids: list[UUID] = Field(min_length=1)
    group_id: UUID
    enrolled_at: date
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class EnrollmentUpdate(ORMModel):
    left_at: date | None = None
    status: EnrollmentStatus | None = None


class EnrollmentResponse(TimestampedSchema, EnrollmentBase):
    student: StudentDetailResponse
    group: GroupResponse
