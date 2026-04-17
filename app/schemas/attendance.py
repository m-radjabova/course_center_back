from uuid import UUID

from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.enums import AttendanceStatus
from app.schemas.profiles import StudentDetailResponse


class AttendanceBase(ORMModel):
    lesson_id: UUID
    enrollment_id: UUID
    student_id: UUID
    status: AttendanceStatus = AttendanceStatus.PRESENT
    note: str | None = None


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(ORMModel):
    status: AttendanceStatus | None = None
    note: str | None = None


class AttendanceResponse(TimestampedSchema, AttendanceBase):
    student: StudentDetailResponse
