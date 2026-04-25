from datetime import date, datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.users import UserResponse


class TeacherProfileBase(ORMModel):
    specialization: str | None = Field(default=None, max_length=120)
    bio: str | None = None
    hired_at: date | None = None


class TeacherProfileCreate(TeacherProfileBase):
    pass


class TeacherProfileUpdate(ORMModel):
    specialization: str | None = Field(default=None, max_length=120)
    bio: str | None = None
    hired_at: date | None = None


class TeacherProfileResponse(TimestampedSchema, TeacherProfileBase):
    user_id: UUID


class StudentProfileBase(ORMModel):
    parent_name: str | None = Field(default=None, max_length=120)
    parent_phone: str | None = Field(default=None, max_length=30)
    notes: str | None = None
    extra_info: str | None = None


class StudentProfileCreate(StudentProfileBase):
    created_by_teacher_id: UUID | None = None


class StudentProfileUpdate(ORMModel):
    parent_name: str | None = Field(default=None, max_length=120)
    parent_phone: str | None = Field(default=None, max_length=30)
    notes: str | None = None
    extra_info: str | None = None


class StudentProfileResponse(TimestampedSchema, StudentProfileBase):
    user_id: UUID
    created_by_teacher_id: UUID | None = None
    telegram_chat_id: str | None = None
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    telegram_connected_at: datetime | None = None
    telegram_last_credentials_sent_at: datetime | None = None


class TeacherDetailResponse(UserResponse):
    teacher_profile: TeacherProfileResponse | None = None


class StudentDetailResponse(UserResponse):
    student_profile: StudentProfileResponse | None = None
    active_group_ids: list[UUID] = Field(default_factory=list)
    active_group_names: list[str] = Field(default_factory=list)


class StudentListResponse(ORMModel):
    items: list[StudentDetailResponse]
    total: int
    active_total: int
    page: int
    limit: int
    pages: int
