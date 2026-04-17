from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.profiles import StudentDetailResponse, TeacherDetailResponse


class GradeBase(ORMModel):
    lesson_id: UUID
    enrollment_id: UUID
    student_id: UUID
    teacher_id: UUID | None = None
    score: Decimal = Field(ge=0, le=100)
    note: str | None = None


class GradeCreate(GradeBase):
    pass


class GradeUpdate(ORMModel):
    teacher_id: UUID | None = None
    score: Decimal | None = Field(default=None, ge=0, le=100)
    note: str | None = None


class GradeResponse(TimestampedSchema, GradeBase):
    student: StudentDetailResponse
    teacher: TeacherDetailResponse | None = None
