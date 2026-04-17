from datetime import date, time
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from app.models.enums import AttendanceStatus, EnrollmentStatus, GroupStatus, LessonStatus, PaymentStatus
from app.schemas.common import ORMModel, TimestampedSchema
from app.schemas.user import UserOut


class CourseBase(ORMModel):
    title: str = Field(min_length=3, max_length=120)
    slug: str = Field(min_length=3, max_length=140)
    description: str | None = None
    duration_months: int = Field(ge=1, le=36)
    monthly_fee: Decimal = Field(ge=0)
    lessons_per_week: int = Field(ge=1, le=7)
    is_active: bool = True


class CourseCreate(CourseBase):
    pass


class CourseUpdate(ORMModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=140)
    description: str | None = None
    duration_months: int | None = Field(default=None, ge=1, le=36)
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    lessons_per_week: int | None = Field(default=None, ge=1, le=7)
    is_active: bool | None = None


class CourseOut(TimestampedSchema, CourseBase):
    pass


class CourseGroupBase(ORMModel):
    course_id: UUID
    teacher_id: UUID | None = None
    name: str = Field(min_length=2, max_length=120)
    room: str | None = Field(default=None, max_length=60)
    capacity: int = Field(ge=1, le=100)
    schedule_summary: str | None = Field(default=None, max_length=255)
    start_date: date
    end_date: date | None = None
    status: GroupStatus = GroupStatus.PLANNED


class CourseGroupCreate(CourseGroupBase):
    pass


class CourseGroupUpdate(ORMModel):
    course_id: UUID | None = None
    teacher_id: UUID | None = None
    name: str | None = Field(default=None, min_length=2, max_length=120)
    room: str | None = Field(default=None, max_length=60)
    capacity: int | None = Field(default=None, ge=1, le=100)
    schedule_summary: str | None = Field(default=None, max_length=255)
    start_date: date | None = None
    end_date: date | None = None
    status: GroupStatus | None = None


class CourseGroupOut(TimestampedSchema, CourseGroupBase):
    course: CourseOut
    teacher: UserOut | None = None


class EnrollmentCreate(ORMModel):
    student_id: UUID
    enrolled_on: date
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class EnrollmentUpdate(ORMModel):
    status: EnrollmentStatus | None = None


class EnrollmentOut(TimestampedSchema):
    group_id: UUID
    student_id: UUID
    enrolled_on: date
    status: EnrollmentStatus
    student: UserOut


class LessonBase(ORMModel):
    group_id: UUID
    teacher_id: UUID | None = None
    lesson_date: date
    start_time: time
    end_time: time
    order_index: int = Field(default=1, ge=1, le=200)
    is_exam: bool = False
    topic: str | None = Field(default=None, max_length=255)
    homework: str | None = None
    notes: str | None = None
    status: LessonStatus = LessonStatus.PLANNED


class LessonCreate(LessonBase):
    pass


class LessonUpdate(ORMModel):
    teacher_id: UUID | None = None
    lesson_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    order_index: int | None = Field(default=None, ge=1, le=200)
    is_exam: bool | None = None
    topic: str | None = Field(default=None, max_length=255)
    homework: str | None = None
    notes: str | None = None
    status: LessonStatus | None = None


class LessonOut(TimestampedSchema, LessonBase):
    teacher: UserOut | None = None


class AttendanceCreate(ORMModel):
    enrollment_id: UUID
    student_id: UUID
    status: AttendanceStatus = AttendanceStatus.PRESENT
    homework_score: int | None = Field(default=None, ge=0, le=100)
    exam_score: int | None = Field(default=None, ge=0, le=100)
    comment: str | None = None


class AttendanceUpdate(ORMModel):
    status: AttendanceStatus | None = None
    homework_score: int | None = Field(default=None, ge=0, le=100)
    exam_score: int | None = Field(default=None, ge=0, le=100)
    comment: str | None = None


class AttendanceOut(TimestampedSchema):
    lesson_id: UUID
    enrollment_id: UUID
    student_id: UUID
    status: AttendanceStatus
    homework_score: int | None = None
    exam_score: int | None = None
    comment: str | None = None
    student: UserOut


class MonthlyPaymentCreate(ORMModel):
    enrollment_id: UUID
    student_id: UUID
    period_month: date
    amount_due: Decimal = Field(ge=0)
    amount_paid: Decimal = Field(default=0, ge=0)
    status: PaymentStatus = PaymentStatus.PENDING
    note: str | None = None


class MonthlyPaymentUpdate(ORMModel):
    amount_due: Decimal | None = Field(default=None, ge=0)
    amount_paid: Decimal | None = Field(default=None, ge=0)
    status: PaymentStatus | None = None
    note: str | None = None


class MonthlyPaymentOut(TimestampedSchema):
    enrollment_id: UUID
    student_id: UUID
    group_id: UUID
    period_month: date
    amount_due: Decimal
    amount_paid: Decimal
    status: PaymentStatus
    note: str | None = None
    student: UserOut | None = None


class StudentMonthFilter(ORMModel):
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)


class StudentMonthLessonRow(ORMModel):
    lesson_id: UUID
    lesson_date: date
    order_index: int
    topic: str | None = None
    is_exam: bool
    attendance_status: AttendanceStatus | None = None
    homework_score: int | None = None
    exam_score: int | None = None
    comment: str | None = None


class StudentMonthlyJournalOut(ORMModel):
    student: UserOut
    group_id: UUID
    year: int
    month: int
    lessons: list[StudentMonthLessonRow]
    attendance_summary: dict[str, int]
    average_homework_score: float | None = None
    average_exam_score: float | None = None
    payments: list[MonthlyPaymentOut]
